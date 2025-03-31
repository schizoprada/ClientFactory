# ~/ClientFactory/src/clientfactory/core/resource.py
"""
Resource Module
---------------
Defines the core Resource class and related components for organizing API endpoints.
The Resource class provides a logical grouping of related API endpoints
and handles the conversion of method calls to HTTP requests
"""
from __future__ import annotations
import re, inspect, typing as t
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urlunparse
from clientfactory.log import log

from clientfactory.core.request import Request, RequestMethod, RM
from clientfactory.core.session import Session
from clientfactory.core.payload import Payload
from clientfactory.declarative import DeclarativeContainer
from clientfactory.backends.base import Backend, BackendType

class ResourceError(Exception):
    """Base exception for resource-related errors"""
    pass

@dataclass
class MethodConfig:
    """Configuration for a resource method"""
    name: str
    method: RequestMethod
    path: t.Optional[str] = None
    preprocess: t.Optional[t.Callable[[Request], Request]] = None
    postprocess: t.Optional[t.Callable[[t.Any], t.Any]] = None
    payload: t.Optional[Payload] = None
    description: str = ""


@dataclass
class ResourceConfig:
    """Configuration for a resource endpoint"""
    name: str
    path: str
    methods: t.Dict[str, MethodConfig] = field(default_factory=dict)
    children: t.Dict[str, 'ResourceConfig'] = field(default_factory=dict)
    parent: t.Optional[t.Union['ResourceConfig', t.Any]] = None
    backend: t.Optional[Backend] = None

class Resource(DeclarativeContainer):
    """
    Base resource class that handles endpoint operations.

    A Resource represents the logical grouping of API endpoints.
    It handles the conversion of method calls into HTTP requests,
    manages child resources, and provides a clear mapping between
    API structure and code.

    Resources can be used directly or as base classes for more specific
    API resources. They support nesting to represent API hierarchies.
    """

    __declarativetype__ = 'resource'
    path: str = ""
    name: t.Optional[str] = None
    backend: t.Optional[Backend] = None


    def  __init__(self, session: Session, config: ResourceConfig, backend: t.Optional[Backend] = None):
        self._session = session
        self._config = config
        #log.debug(f"Initializing resource: {config.name} with path: {config.path}")
        #log.debug(f"Resource parent: {config.parent}")

        self._backend = (backend or getattr(config, 'backend', None))

        self._setup()

    def _getfullpath(self, path: t.Optional[str] = None) -> str:
        """Construct full resource path including parents"""
        parts = []
        current = self._config

        while current:
            if hasattr(current, 'path') and current.path:
                parts.append(current.path)
                #log.debug(f"Adding path part: {current.path}")
            current = getattr(current, 'parent', None)
            #log.debug(f"Moving to parent: {current}")

        # reverse to get root-> leaf order
        parts.reverse()
        #log.debug(f"Path parts after reverse: {parts}")

        # add method path if provided
        if path:
            parts.append(path)
            #log.debug(f"Added method path: {path}")

        finalpath = '/'.join(part.strip('/') for part in parts if part)
        #log.debug(f"Final constructed path: {finalpath}")
        return finalpath

    def _substitutepathparams(self, path: str, args: tuple, kwargs: dict) -> str:
        """Replace path parameters with values from args or kwargs"""
        if not path:
            return path

        parampattern = r'\{([^}]+)\}'
        params = re.findall(parampattern, path)
        #log.debug(f"Path parameters found: {params}")

        if not params:
            return path

        if args:
            #log.debug(f"Using positional args for path params: {args}")
            if len(args) != len(params):
                raise ResourceError(
                    f"Expected {len(params)} positional arguments "
                    f"({', '.join(params)}), got {len(args)}"
                )
            for param, arg in zip(params, args):
                path = path.replace(f"{{{param}}}", str(arg))
        else:
            #log.debug(f"Using keyword args for path params: {kwargs}")
            for param in params:
                if param not in kwargs:
                    raise ResourceError(f"Missing required path parameter: '{param}'")
                path = path.replace(f"{{{param}}}", str(kwargs.pop(param)))
                #log.debug(f"Replaced param {param} in path, now: {path}")

        return path

    def _getbaseurl(self) -> t.Optional[str]:
        """Get the base URL from the client"""
        current = self._config.parent
        #log.debug(f"Getting base URL, starting with parent: {current}")

        while current:
            #log.debug(f"Checking parent: {current}")
            if hasattr(current, 'baseurl'):
                #log.debug(f"Found baseurl: {current.baseurl}")
                return current.baseurl

            if hasattr(current, '_config') and hasattr(current._config, 'baseurl'):
                #log.debug(f"Found baseurl on parent's config: {current._config.baseurl}")
                return current._config.baseurl


            current = getattr(current, 'parent', None)
            #log.debug(f"Moving to next parent: {current}")



        #log.debug("No baseurl found in parent chain, trying class metadata")
        if hasattr(self.__class__, 'getmetadata'):
            try:
                baseurl = self.__class__.getmetadata('baseurl')
                if baseurl:
                    #log.debug(f"Found baseurl in class metadata: {baseurl}")
                    return baseurl
            except:
                pass
        #log.debug("No baseurl found in parent chain or class metadata")
        return None

    def _buildurl(self, path: str) -> str:
        """Build a full URL from base URL and path"""
        baseurl = self._getbaseurl()
        #log.debug(f"Building URL with baseurl: {baseurl} and path: {path}")

        if not baseurl:
            #log.debug(f"No baseurl available, returning path only: {path}")
            return path

        # Ensure baseurl has a trailing slash for proper joining
        if not baseurl.endswith('/'):
            baseurl += '/'
            #log.debug(f"Added trailing slash to baseurl: {baseurl}")

        # If path starts with slash, remove it for proper joining
        if path.startswith('/'):
            path = path[1:]
            #log.debug(f"Removed leading slash from path: {path}")

        # Join paths properly
        if ':' in path:
            path = f"./{path}" # treat paths with colons as relative for urljoin
        fullurl = urljoin(baseurl, path)
        #log.debug(f"Final URL after joining: {fullurl}")
        return fullurl

    def _buildrequest(self, cfg: MethodConfig, *args, **kwargs) -> Request:
        """Build a request object for the method"""
        #log.debug(f"Building request for method: {cfg.name} with path: {cfg.path}")
        #log.debug(f"Args: {args}, Kwargs: {kwargs}")
        #log.debug(f"Config: {cfg.__dict__}")

        # Get the resource path
        resourcepath = self._getfullpath(cfg.path)
        #log.debug(f"Full resource path: {resourcepath}")

        # Substitute path parameters
        resourcepath = self._substitutepathparams(resourcepath, args, kwargs)
        #log.debug(f"Path after parameter substitution: {resourcepath}")

        # Build the complete URL
        url = self._buildurl(resourcepath)
        #log.debug(f"Final URL: {url}")

        # Initialize request kwargs
        reqkwargs = {}

        # Process payload if available
        if cfg.payload:
            try:
                #log.debug(f"Processing payload for method {cfg.method}")
                processedpayload = cfg.payload.apply(kwargs)

                if cfg.method in (RM.POST, RM.PUT, RM.PATCH):
                    reqkwargs['json'] = processedpayload
                    #log.debug(f"Added JSON payload: {processedpayload}")
                else:
                    reqkwargs['params'] = processedpayload
                    #log.debug(f"Added query params: {processedpayload}")
            except Exception as e:
                #log.debug(f"Error processing payload: {str(e)}")
                raise ResourceError(f"Error processing payload: {str(e)}")
        else:
            # if no payload, pass all kwargs to the request
            for k, v in kwargs.items():
                if k in ['headers', 'cookies', 'data', 'json', 'params', 'files', 'config', 'context']:
                    reqkwargs[k] = v

        # Add additional request parameters that aren't part of the payload
        for k, v in kwargs.items():
            if k in ['headers', 'cookies', 'data', 'files', 'config', 'context']:
                reqkwargs[k] = v

        #log.debug(f"Creating request with method ({cfg.method}) for url ({url}) with kwargs: {reqkwargs}")

        request = Request(
            method=cfg.method,
            url=url,
            **reqkwargs
        )

        if self._backend:
            request = self._backend.preparerequest(request, kwargs)

        #log.debug(f"Created request: {request}")
        return request

    def _createmethod(self, cfg: MethodConfig) -> t.Callable:
        """Create a callable method from method configuration"""
        def method(*args, **kwargs):
            #log.debug(f"DEBUGGING - Method call: {cfg.name}")
            #log.debug(f"Method config: {cfg.__dict__}")
            #log.debug(f"Args: {args}")
            #log.debug(f"Kwargs: {kwargs}")
            #log.debug(f"Calling method: {cfg.name}")
            request = self._buildrequest(cfg, *args, **kwargs)
            #log.debug(f"Built request headers: {request.headers}")
            if cfg.preprocess:
                #log.debug(f"Applying preprocessor to request")
                request = cfg.preprocess(request)

            #log.debug(f"Sending request: {request}")
            response = self._session.send(request)
            #log.debug(f"Received response: status={response.statuscode}")

            if self._backend:
                response = self._backend.processresponse(response)

            if cfg.postprocess:
                #log.debug(f"Applying postprocessor to response")
                return cfg.postprocess(response)
            return response
        method.__name__ = cfg.name
        method.__doc__ = cfg.description
        return method

    def _setup(self):
        """Set up methods and child resources"""
        # set up resource methods
        for name, mcfg in self._config.methods.items():
            #log.debug(f"Setting up method: {name}")
            if not hasattr(self, name):
                setattr(self, name, self._createmethod(mcfg))

        for name, ccfg in self._config.children.items():
            #log.debug(f"Setting up child resource: {name}")
            if not hasattr(self, name):
                ccfg.parent = self._config
                setattr(self, name, Resource(self._session, ccfg))

    @classmethod
    def _processclassattributes(cls) -> None:
        """Process resource-specific class attributes."""
        #log.debug(f"DeclarativeResource: starting attribute processing for ({cls.__name__})")
        #log.debug(f"DeclarativeResource: current metadata before processing: {cls.__metadata__}")

        # Set name FIRST, before any inheritance
        if ('name' not in cls.__metadata__):
            cls.__metadata__['name'] = cls.__name__.lower()
            #log.debug(f"DeclarativeResource: set name to ({cls.__metadata__['name']}) for: {cls.__name__}")
        else:
            pass
            #log.debug(f"DeclarativeResource: name already set to ({cls.__metadata__['name']}) for: {cls.__name__}")

        # Then do normal processing
        #log.debug(f"DeclarativeResource: calling super()._processclassattributes for: {cls.__name__}")
        super()._processclassattributes()
        #log.debug(f"DeclarativeResource: returned from super()._processclassattributes for: {cls.__name__}")
        #log.debug(f"DeclarativeResource: metadata after super(): {cls.__metadata__}")

        # Process path after other attributes
        if ('path' not in cls.__metadata__) and (hasattr(cls, 'path')):
            cls.__metadata__['path'] = cls.path.lstrip('/').rstrip('/')
            #log.debug(f"DeclarativeResource: extracted path ({cls.path}) from: {cls.__name__}")

        #log.debug(f"DeclarativeResource: completed processing for ({cls.__name__}) - final metadata: {cls.__metadata__}")


    @classmethod
    def getfullpath(cls) -> str:
        """
        Get the full path of the resource including parent paths.

        Traverses the parent to chain to build the complete resource path.
        """
        pathparts = []
        current = cls
        seen = set()

        while current and id(current) not in seen:
            seen.add(id(current))
            if hasattr(current, '__metadata__') and ('path' in current.__metadata__):
                if (mpath:=current.__metadata__.get('path', '')):
                    pathparts.append(mpath.lstrip('/').rstrip('/'))
                current = current.__metadata__.get('parent')
            else:
                break


        pathparts.reverse()

        return '/' + '/'.join(pathparts)


    @classmethod
    def getmethods(cls) -> dict:
        """Get all declarative methods defined on this resource."""
        return cls.__metadata__.get('methods', {})

    @classmethod
    def getnestedresources(cls) -> dict:
        """Get all nested resources defined on this resource."""
        return cls.__metadata__.get('components', {})


class ResourceBuilder:
    """Builder for creating Resource instances with fluent configuration"""

    def __init__(self, name: str, path: str = ""):
        """Initialize builder with resource name and path"""
        self._config = ResourceConfig(
            name=name,
            path=(path or name.lower())
        )
        self._session = None
        #log.debug(f"Created ResourceBuilder for {name} with path {self._config.path}")

    def path(self, path: str) -> ResourceBuilder:
        """Set the resource path"""
        self._config.path = path
        #log.debug(f"Set resource path to: {path}")
        return self

    def addmethod(
        self,
        name: str,
        method: RequestMethod,
        path: t.Optional[str] = None,
        payload: t.Optional[Payload] = None,
        preprocess: t.Optional[t.Callable] = None,
        postprocess: t.Optional[t.Callable] = None,
        description: str = ""
    ) -> ResourceBuilder:
        """Add a method to the resource"""
        self._config.methods[name] = MethodConfig(
            name=name,
            method=method,
            path=path,
            payload=payload,
            preprocess=preprocess,
            postprocess=postprocess,
            description=description
        )
        #log.debug(f"Added method {name} with path {path}")
        return self

    def addchild(self, name: str, child: (ResourceBuilder | ResourceConfig)) -> ResourceBuilder:
        """Add a child resource"""
        if isinstance(child, ResourceBuilder):
            childcfg = child._config
        else:
            childcfg = child

        childcfg.parent = self._config
        self._config.children[name] = childcfg
        #log.debug(f"Added child resource: {name}")
        return self

    def session(self, session: Session) -> ResourceBuilder:
        """Set the session to use for this resource"""
        self._session = session
        #log.debug(f"Set session for resource")
        return self

    def build(self) -> Resource:
        """Build and return a Resource with the configured options"""
        if not self._session:
            #log.error("Cannot build resource: Session is required")
            raise ResourceError("Session is required to build a Resource")
        #log.debug(f"Building resource: {self._config.name}")
        return Resource(self._session, self._config)


# shorthand functions for method definition
def decoratormethod(method: RequestMethod, path: t.Optional[str] = None, **kwargs) -> t.Callable[[t.Callable], t.Callable]:
    """Method to create a RequestMethod decorator method"""
    def decorator(func):
        func._methodcfg = MethodConfig(
            name=func.__name__,
            method=method,
            path=path,
            **kwargs
        )
        #log.debug(f"Created method decorator for {func.__name__} with path {path}")
        return func
    return decorator

def get(path: t.Optional[str] = None, **kwargs)-> t.Callable[[t.Callable], t.Callable]:
    return decoratormethod(RequestMethod.GET, path, **kwargs)

def post(path: t.Optional[str] = None, **kwargs)-> t.Callable[[t.Callable], t.Callable]:
    return decoratormethod(RequestMethod.POST, path, **kwargs)

def put(path: t.Optional[str] = None, **kwargs)-> t.Callable[[t.Callable], t.Callable]:
    return decoratormethod(RequestMethod.PUT, path, **kwargs)

def patch(path: t.Optional[str] = None, **kwargs)-> t.Callable[[t.Callable], t.Callable]:
    return decoratormethod(RequestMethod.PATCH, path, **kwargs)

def delete(path: t.Optional[str] = None, **kwargs)-> t.Callable[[t.Callable], t.Callable]:
    return decoratormethod(RequestMethod.DELETE, path, **kwargs)
