# ~/ClientFactory/src/clientfactory/core/response.py
"""
Response Class
--------------
Defines the core Response object and related components for handling HTTP responses.
The Response class encapsulates all data returned from an HTTP request,
including status code, headers, and content.
"""
from __future__ import annotations
import json, typing as t
from dataclasses import dataclass, field
from http import HTTPStatus
from urllib.parse import parse_qs as parseqs

from clientfactory.core.request import Request


class ResponseError(Exception):
    """Base exception for response-related errors"""
    pass

class HTTPError(ResponseError):
    """Raised when response indicates HTTP error"""
    def __init__(self, response: 'Response') -> None:
        self.response = response
        super().__init__(f"HTTP {response.statuscode} {response.reason}: {response.url}")

class ExtractionError(ResponseError):
    """Raised when data extraction fails"""
    pass

@dataclass
class Response:
    """
    HTTP Response representaion

    Encapsulates the data returned from an HTTP request including status, headers, and content.
    Provides methods for data extraction and validation.
    """
    statuscode: int
    headers: dict
    rawcontent: bytes
    request: Request
    cookies: dict = field(default_factory=dict)
    _parsedjson: t.Optional[t.Any] = field(default=None, repr=False)

    @property
    def ok(self) -> bool:
        """Whether the request was successful (200-299)"""
        return (200 <= self.statuscode < 300)

    @property
    def reason(self) -> str:
        """HTTP status reason phrase"""
        return HTTPStatus(self.statuscode).phrase

    @property
    def url(self) -> str:
        """URL that was requested"""
        return self.request.url

    @property
    def content(self) -> bytes:
        """Raw response content"""
        return self.rawcontent

    @property
    def text(self) -> str:
        """Response content as text"""
        return self.rawcontent.decode('utf-8')

    def json(self, **kwargs) -> t.Any:
        """
        Parse response content as JSON
        Results are cached after first call
        """
        if self._parsedjson is None:
            try:
                self._parsedjson = json.loads(self.text, **kwargs)
            except json.JSONDecodeError as e:
                raise ResponseError(f"Invalid JSON: {str(e)}")
        return self._parsedjson

    def raiseforstatus(self) -> None:
        """Raise HTTPError if status indicates error"""
        if not self.ok:
            raise HTTPError(self)


    def clone(self, **updates) -> Response:
        params = self.__dict__.copy()

        # copy mutable objects to avoid shared references
        if 'headers' in params:
            params['headers'] = params['headers'].copy()

        # apply updates
        params.update(params)

        return self.__class__(**params)


    def _extractjson(self, parts: list, default: t.Any) -> t.Any:
        """Extract value from JSON response"""
        try:
            data = self.json()
            for part in parts:
                if isinstance(part, int):
                    data = data[part]
                else:
                    data = data[part] # whats the point of checking for the instance type then?
            return data
        except (KeyError, IndexError, TypeError):
            return default

    def _extractheaders(self, parts: list, default: t.Any) -> t.Any:
        """Extract value from response headers"""
        if not parts:
            return default
        headername = parts[0].lower()
        for k, v in self.headers.items():
            if k.lower() == headername:
                return v
        return default

    def _extractcookies(self, parts: list, default: t.Any) -> t.Any:
        if not parts:
            return default
        cookiename = parts[0]
        return self.cookies.get(cookiename, default)

    def _extractquery(self, parts: list, default: t.Any) -> t.Any:
        """Extract value from request URL query parameters"""
        if not parts:
            return default
        try:
            if '?' in self.request.url:
                qstring = self.request.url.split('?', 1)[1]
                qparams = parseqs(qstring)
                if (paramname:=parts[0]) in qparams:
                    values = qparams[paramname]
                    return values[0] if values else default
            return default
        except Exception:
            return default

    def extract(self, path: str, default: t.Any = None) -> t.Any:
        """
        Extract value from response using path notation

        Path notation examples:
            - "json.data.items[0].name" - Get name fo the first item from JSON
            - "headers.content-type" - Get content-type header
            - "query.q" - Get q parameter from request URL
        """
        extractors = {
            'json': self._extractjson,
            'headers': self._extractheaders,
            'query': self._extractquery,
            'cookies': self._extractcookies
        }
        returndefault = lambda x, y: default
        try:
            parts = path.split('.', 1)
            source = parts[0].lower()

            if len(parts) > 1:
                remaining = parts[1]
                processed = [] # process array notation
                for part in remaining.split('.'):
                    if ('[' in part) and (']' in part):
                        idxparts = part.split('[')
                        key = idxparts[0]
                        idx = int(idxparts[1].rstrip(']'))
                        processed.extend([key, idx])
                    else:
                        processed.append(part)
            else:
                processed = []

            extractor = extractors.get(source, returndefault)
            return extractor(processed, default)
        except Exception as e:
            return default


    def __bool__(self) -> bool:
        """Truth value is based on ok property"""
        return self.ok

T = t.TypeVar('T')

class ResponseMapper:
    """Maps response data to object attributes for easy data extraction"""

    @staticmethod
    def Map(response: Response, mapping: dict, basepath: str = "json") -> t.Dict[str, t.Any]:
        """Map response data to dictionary using specified mapping"""
        result = {}
        for k, path in mapping.items():
            if ('.' in path) and (path.split('.')[0] in ('json', 'headers', 'query')):
                extractpath = path
            else:
                extractpath = f"{basepath}.{path}"
            result[k] = response.extract(extractpath)
        return result

    @staticmethod
    def ToObject(response: Response, cls: t.Type[T], mapping: dict, basepath: str = "json") -> T:
        """Map response data to an instance of the specified class"""
        data = ResponseMapper.Map(response, mapping, basepath)
        return cls(**data)

    @staticmethod
    def ToObjects(response: Response, cls: t.Type[T], mapping: dict, itemspath: str = "json.data", basepath: str = "") -> t.List[T]:
        """Map response data to a list of objects"""
        items = response.extract(itemspath, [])
        result = []

        for idx, item in enumerate(items):
            tempresponse = Response(
                statuscode=response.statuscode,
                headers=response.headers,
                rawcontent=response.rawcontent,
                request=response.request,
                _parsedjson=item
            )

            obj = ResponseMapper.ToObject(tempresponse, cls, mapping, basepath)
            result.append(obj)

        return result
