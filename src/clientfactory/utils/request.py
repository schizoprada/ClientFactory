# ~/clientfactory/utils/request.py
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field, fields, asdict
from enum import Enum
import urllib.parse
from copy import deepcopy

class RequestMethod(str, Enum):
    """HTTP Request Methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    NA = "NA" # for binding methods in methodconfig that arent request methods

class RequestError(Exception):
    """Base Exception for Request Exceptions"""
    pass

class ValidationError(RequestError):
    """Raised when Request Validation fails"""
    pass

@dataclass
class RequestConfig:
    """Configuration for request behavior"""
    timeout: float = 30.0
    maxretries: int = 3
    retrybackoff: float = 1.5
    verifyssl: bool = True
    allowredirects: bool = True
    stream: bool = False

@dataclass
class Request:
    """HTTP Request with all necessary information to execute"""
    method: RequestMethod
    url: str
    params: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    cookies: dict = field(default_factory=dict)
    data: t.Optional[dict] = None
    json: t.Optional[dict] = None
    files: t.Optional[dict] = None
    config: RequestConfig = field(default_factory=RequestConfig)
    kwargs: dict = field(default_factory=dict)
    prepped: bool = False

    def __del__(self):
        if hasattr(self, '_filecleanup'):
            self._filecleanup()

    def __post_init__(self):
        """Validate initial state"""
        if isinstance(self.method, str):
            self.method = RequestMethod(self.method.upper())
        self.validate()

    def validate(self):
        """Validates request state"""
        if not self.url: raise ValidationError("URL is required")

        if self.data is not None and self.json is not None: raise ValidationError("Cannot specify both `data` and `json`")

        if self.method == RequestMethod.GET and (self.data or self.json): raise ValidationError("GET requests cannot have body")

    def prepare(self) -> Request:
        if self.prepped: return self

        prepared = deepcopy(self)

        # Normalize URL
        prepared.url = urllib.parse.urljoin(prepared.url, urllib.parse.urlparse(prepared.url).path)

        # ensure headers dict exists
        prepared.headers = prepared.headers or {}

        # add content type if needed
        if prepared.json is not None and 'content-type' not in prepared.headers:
            prepared.headers['content-type'] = 'application/json'

        prepared.prepped = True
        return prepared

    def WITH(self, **updates) -> Request:
        # Create a new dict with copies of dict fields, originals of others
        fieldz = {
            field.name: (val.copy() if isinstance(val:=getattr(self, field.name), dict) else val)
            for field in fields(self)  # Use the field object, not its name
        }

        # Fields that should be updated (merged) rather than replaced
        UPDATEABLE = {'params', 'headers', 'cookies'}

        return self.__class__(**{
            **fieldz,  # Start with our copied fields
            **{k: fieldz[k].update(v) or fieldz[k]  # Dict update returns None, so or returns the dict
            if k.lower() in UPDATEABLE and v is not None  # Merge updateable dicts if value provided
            else RequestConfig(**{**asdict(fieldz[k]), **v})  # Handle RequestConfig special case
            if k == 'config' and isinstance(v, dict)  # If updating config with dict
            else v  # Otherwise just use the new value
            for k, v in updates.items()  # Process each update
            }
        })



class RequestFactory:
    """Factory for creating requests with shared configuration"""
    def __init__(self, baseurl:str="", defaultcfg: t.Optional[RequestConfig]=None):
        self.baseurl = baseurl.rstrip('/')
        self.defaultcfg = defaultcfg or RequestConfig()

    def create(self, method:(str | RequestMethod), path:str, **kwargs) -> Request:
        url = f"{self.baseurl}/{path.lstrip('/')}" if self.baseurl else path
        return Request(
            method=method,
            url=url,
            config=self.defaultcfg,
            **kwargs
        )

    def get(self, path: str, **kwargs) -> Request:
        return self.create(RequestMethod.GET, path, **kwargs)

    def post(self, path: str, **kwargs) -> Request:
        return self.create(RequestMethod.POST, path, **kwargs)

    def put(self, path: str, **kwargs) -> Request:
        return self.create(RequestMethod.PUT, path, **kwargs)

    def patch(self, path: str, **kwargs) -> Request:
        return self.create(RequestMethod.PATCH, path, **kwargs)

    def delete(self, path: str, **kwargs) -> Request:
        return self.create(RequestMethod.DELETE, path, **kwargs)
