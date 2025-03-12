# ~/clientfactory/utils/response.py
from __future__ import annotations
from re import L
import typing as t, functools as fn
import json
from dataclasses import dataclass, field, asdict
from http import HTTPStatus
from urllib.parse import parse_qs as parseqs
#from clientfactory.session.cookies.core import Cookie
from loguru import logger as log

class ResponseError(Exception):
    """Base exception for response-related errors"""
    pass

class HTTPError(ResponseError):
    """Raised when response indicates HTTP error"""
    def __init__(self, response: Response):
        self.response = response
        super().__init__(
            f"HTTP {response.status_code} {response.reason}: {response.url}"
        )

class ExtractionError(ResponseError):
    """Raised when path extraction fails"""
    pass

class ObjectMap:
    """Factory and base class for response object mapping"""
    def __new__(cls, **kwargs):
        # when called directly e.g. ObjectMap(**kwargs)
        if cls is ObjectMap:
            return type('GeneratedObjectMap', (ObjectMap,), kwargs)
        return super().__new__(cls)

    def __init__(self, **values):
        # when instantiated by itemize() set actual values
        for k,v in values.items():
            setattr(self, k, v)

T = t.TypeVar('T')

@dataclass
class ResponseMap(t.Generic[T]):
    objectmap: t.Type[T]
    objectspath: t.Optional[str] = None
    transform: t.Optional[t.Callable[[t.Dict], t.List[t.Dict]]] = None


@dataclass
class Response:
    """HTTP Response representation"""
    status_code: int
    headers: dict
    raw_content: bytes
    request: "Request"  # from request.py
    _parsedjson: t.Optional[t.Any] = field(default=None, repr=False)
    _parsedcookies: t.Optional[dict[str, "Cookie"]] = field(default=None, repr=False)

    @property
    def ok(self) -> bool:
        """Whether the request was successful"""
        return 200 <= self.status_code < 300

    @property
    def reason(self) -> str:
        """HTTP status reason"""
        return HTTPStatus(self.status_code).phrase

    @property
    def url(self) -> str:
        """URL that was requested"""
        return self.request.url

    @property
    def content(self) -> bytes:
        """Raw response content"""
        return self.raw_content

    @property
    def text(self) -> str:
        """Response content as text"""
        return self.raw_content.decode('utf-8')

    def json(self, **kwargs) -> t.Any:
        """
        Parse response content as JSON
        Results are cached after first call
        """
        if self._parsedjson is None:
            try:
                self._parsedjson = json.loads(self.text, **kwargs)
            except json.JSONDecodeError as e:
                raise ResponseError(f"Invalid JSON response: {e}")
        return self._parsedjson

    def raise_for_status(self) -> None:
        """Raise HTTPError if status indicates error"""
        if not self.ok:
            raise HTTPError(self)

    def __bool__(self) -> bool:
        """Truth value is based on ok property"""
        return self.ok

    def WITH(self, **updates) -> Response:
        """Create new response with updates"""
        fields = {
            'status_code': self.status_code,
            'headers': self.headers.copy(),
            'raw_content': self.raw_content,
            'request': self.request,
            '_parsedjson': self._parsedjson
        }

        UPDATEABLE = {'headers'}
        for k, v in updates.items():
            if k.lower() in UPDATEABLE and v is not None:
                fields[k].update(v)  # merge dicts for updateable fields
            else:
                fields[k] = v  # replace for other fields

        return self.__class__(**fields)

    @property
    def cookies(self) -> dict[str, str]:  # should probably have a property for headers too while we're at i'
        if self._parsedcookies is None:
            self._parsedcookies = {}
            from clientfactory.session.cookies.core import Cookie
            cookieheaders = [] # this could probably be a comprehension
            for k, v in self.headers.items():
                if k.lower() == 'set-cookie':
                    if isinstance(v, list):
                        cookieheaders.extend(v)
                    else:
                        cookieheaders.append(v)
            for header in cookieheaders:
                try:
                    cookie = Cookie.fromstring(header)
                    self._parsedcookies[cookie.name] = cookie
                except Exception as e:
                    log.warning(f"Response.cookies  | failed to parse cookie from header string: [{header}] | exception: {str(e)}")

        return {name: cookie.value for name, cookie in self._parsedcookies.items()}

    @property
    def cookieobjects(self) -> dict[str, "Cookie"]:
        if self._parsedcookies is None:
            _ = self.cookies # force parsing
        return self._parsedcookies.copy()

    def extract(self, path: (str | t.Iterable[str | int]), delimiter: str = '.', default: t.Any = None) -> t.Any:
        """Extract value using path notation"""
        def extractjson(parts: t.Sequence[t.Union[str, int]]) -> t.Any:
            """Extract value from JSON response using parts sequence"""
            try:
                data = self.json()
                for part in parts:
                    if isinstance(part, int):
                        data = data[part]
                    else:
                        data = data[str(part)]
                return data
            except (KeyError, IndexError) as e:
                raise ExtractionError(f"Response.extract.extractjson | exception: {str(e)}")

        try:
            # Log incoming request
            log.debug(f"Response.extract | Extracting path: [{path}] | Delimiter: [{delimiter}] | Default: [{default}]")

            # Parse path into source and parts
            if isinstance(path, str):
                parts = path.split(delimiter, 1)
                source = parts[0].lower()
                log.debug(f"Response.extract | String path split: {parts}")

                if len(parts) > 1:
                    remaining = parts[1]
                    processed = []
                    log.debug(f"Response.extract | Processing remaining parts: [{remaining}]")

                    for part in remaining.split(delimiter):
                        if ('[' in part) and (']' in part):
                            key, idx = part.split('[')
                            processed.extend([key, int(idx.rstrip(']'))])
                            log.debug(f"Response.extract | Processed array notation: key=[{key}] idx=[{idx.rstrip(']')}]")
                        else:
                            processed.append(part)
                            log.debug(f"Response.extract | Processed simple part: [{part}]")
                else:
                    processed = []
                    log.debug("Response.extract | No remaining parts to process")
            else:
                source = str(path[0]).lower()
                processed = list(path[1:])
                log.debug(f"Response.extract | Iterable path: source=[{source}] parts={processed}")

            log.debug(f"Response.extract | Final processed path: source=[{source}] parts={processed}")

            # Define extractors
            extractmap = {
                'headers': lambda p: next(
                    (v for k, v in self.headers.items()
                    if k.lower() == str(p[0]).lower()),
                    default
                ) if p else default,
                'cookies': lambda p: self.cookies.get(str(p[0]), default) if p else default,
                'json': lambda p: extractjson(p) if p else default,
                'query': lambda p: parseqs(
                    self.request.url.split('?')[-1]
                ).get(str(p[0]), [default])[0] if p else default
            }

            # Validate source
            if source not in extractmap:
                log.warning(f"Response.extract | Unknown source: [{source}]")
                return default

            # Extract value
            try:
                result = extractmap[source](processed)
                log.debug(f"Response.extract | Extraction result: [{result}]")
                return result
            except ExtractionError as e:
                log.warning(f"Response.extract | ExtractionError: {str(e)}")
                return default
            except Exception as e:
                log.error(f"Response.extract | Unexpected error during extraction: {str(e)}")
                return default

        except Exception as e:
            log.error(f"Response.extract | Fatal error processing path: {str(e)}")
            return default

    def itemize(self, mapping: ResponseMap) -> t.List[ObjectMap]:
        """Convert response to standardized objects using mapping"""
        if self.ok:
            try:
                data = self.json()
                if mapping.transform:
                    objects = mapping.transform(data)
                elif mapping.objectspath:
                    objects = self.extract(f"json.{mapping.objectspath}")
                else:
                    objects = [data] if isinstance(data, dict) else data

                # mapping paths from class attributes
                paths = {
                    k:v for k,v in vars(mapping.objectmap).items()
                    if not k.startswith('__')
                }
                items = []
                for obj in objects:
                    item = {}
                    for field, path in paths.items():
                        try:
                            if callable(path):
                                value = path(obj)
                            elif isinstance(path, str) and '.' in path:
                                value = fn.reduce(
                                    lambda d, k: d.get(k, {}),
                                    path.split('.'),
                                    obj
                                )
                            else:
                                value = obj.get(path)
                            item[field] = value
                        except Exception as e:
                            log.warning(f"Response.itemize | Field mapping error | field: {field} | error: {str(e)}")
                            item[field] = None
                    items.append(mapping.objectmap(**item))
                return items
            except Exception as e:
                log.error(f"Response.itemize | exception | {str(e)}")
        return []
