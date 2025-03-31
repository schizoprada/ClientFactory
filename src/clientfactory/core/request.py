# ~/ClientFactory/src/clientfactory/core/request.py
"""
Request Class
-------------
Defines the core Request object and related components for building HTTP requests.
The Request class encapsulates all data needed to make an HTTP Request,
including method, URL, headers, and payload.
"""
from __future__ import annotations
import enum, typing as t, copy as cp
from dataclasses import dataclass, field
import urllib.parse

from clientfactory.log import log

class RequestMethod(str, enum.Enum):
    """HTTP Request Methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


RM = RequestMethod # shorthand

@dataclass
class RequestConfig:
    """Configuration for request behavior"""
    timeout: float = 30.0
    maxretries: int = 3
    retrybackoff: float = 1.5
    verifyssl: bool = True
    allowredirects: bool = True
    stream: bool = False
    randomheaders: bool = False
    randomcookies: bool = False

class RequestError(Exception):
    """Base exception for request-related errors"""
    pass

class ValidationError(RequestError):
    """Raised when request validation fails"""
    pass

@dataclass
class Request:
    """
    HTTP Request with all necessary information to execute.

    Represents a complete HTTP request with method, URL, headers, and optional body data.
    Includes validation and pereparation functionality to ensure the request is ready.
    """
    method: RequestMethod
    url: str
    params: t.Dict[str, t.Any] = field(default_factory=dict)
    headers: t.Dict[str, str] = field(default_factory=dict)
    cookies: t.Dict[str, str] = field(default_factory=dict)
    data: t.Optional[t.Any] = None
    json: t.Optional[t.Dict[str, t.Any]] = None
    files: t.Optional[t.Dict[str, t.Any]] = None
    config: RequestConfig = field(default_factory=RequestConfig)

    # initialization configs
    randomheaders: bool = False

    # additional metadata for internal use
    context: t.Dict[str, t.Any] = field(default_factory=dict)
    prepared: bool = False

    def __post_init__(self):
        """Validate initial state"""
        if isinstance(self.method, str):
            try:
                self.method = RequestMethod(self.method.upper())
            except Exception as e:
                raise ValidationError(e)
        self.validate()

    def validate(self) -> None:
        if not self.url:
            raise ValidationError("URL is required")

        if (self.data is not None) and (self.json is not None):
            raise ValidationError("Cannot specify both 'data' and 'json'")

        if (self.method == RM.GET) and (self.data or self.json):
            raise ValidationError("GET requests cannot have body")

    def prepare(self) -> Request:
        """Prepare the request for execution"""
        if self.prepared:
            return self

        prepared = cp.deepcopy(self)

        # normalize URL
        prepared.url = urllib.parse.urljoin(prepared.url, urllib.parse.urlparse(prepared.url).path)

        # ensure headers dict exists
        prepared.headers = (prepared.headers or {})

        # handle random if toggled
        if self.randomheaders:
            try:
                from fake_headers import Headers as H
                headers = H(headers=True).generate()
                prepared.headers = headers
            except Exception as e:
                log.error(f"Request.prepare | exception: {e}")

        # add content type if needed
        if (prepared.json is not None) and ('content-type' not in {k.lower(): v for k, v in prepared.headers.items()}):
            prepared.headers['Content-Type'] = 'application/json'

        prepared.prepared = True
        return prepared

    def clone(self, **updates) -> Request:
        """Create a new request with updates applied"""
        # new request with current values as base
        params = self.__dict__.copy()

        # deep copies of dicts to avoid shared references
        for k in ['params', 'headers', 'cookies', 'json', 'context']:
            if (k in params) and (isinstance(params[k], dict)):
                params[k] = params[k].copy()

        # handle config updates specially
        if 'config' in updates:
            if isinstance(updates['config'], dict):
                configdict = params['config'].__dict__.copy()
                configdict.update(updates['config'])
                params['config'] = RequestConfig(**configdict)
            elif isinstance(updates['config'], RequestConfig):
                # use provided RequestConfig
                params['config'] = updates['config']
            else:
                raise ValidationError("'config' updates must be either dict or RequestConfig")
            del updates['config']

        # apply all other updates
        params.update(updates)

        # return new instance
        return self.__class__(**params)

class RequestFactory:
    """Factory for creating requests with shared configuration"""

    def __init__(self, baseurl: str = "", defaultconfig: t.Optional[RequestConfig] = None):
        self.baseurl = baseurl.rstrip('/')
        self.defaultconfig = (defaultconfig or RequestConfig())

    def create(self, method: (str | RequestMethod), path: str, **kwargs) -> Request:
        """Create a request with the factory's base URL and config"""
        url = f"{self.baseurl}/{path.lstrip('/')}" if self.baseurl else path
        return Request(
            method=method,
            url=url,
            config=self.defaultconfig,
            **kwargs
        )

    def get(self, path: str, **kwargs) -> Request:
        """Create a GET Request"""
        return self.create(RM.GET, path, **kwargs)

    def post(self, path: str, **kwargs) -> Request:
        """Create a POST Request"""
        return self.create(RM.POST, path, **kwargs)

    def put(self, path: str, **kwargs) -> Request:
        """Create a PUT Request"""
        return self.create(RM.PUT, path, **kwargs)

    def patch(self, path: str, **kwargs) -> Request:
        """Create a PATCH Request"""
        return self.create(RM.PATCH, path, **kwargs)

    def delete(self, path: str, **kwargs) -> Request:
        """Create a DELETE Request"""
        return self.create(RM.DELETE, path, **kwargs)
