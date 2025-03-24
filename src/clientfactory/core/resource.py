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
from loguru import logger as log

from clientfactory.core.request import Request, RequestMethod
from clientfactory.core.session import Session
from clientfactory.core.payload import Payload

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


class Resource:
    """
    Base resource class that handles endpoint operations.

    A Resource represents the logical grouping of API endpoints.
    It handles the conversion of method calls into HTTP requests,
    manages child resources, and provides a clear mapping between
    API structure and code.

    Resources can be used directly or as base classes for more specific
    API resources. They support nesting to represent API hierarchies.
    """

    def  __init__(self, session: Session, config: ResourceConfig):
        self._session = session
        self._config = config
        log.debug(f"Initializing resource: {config.name} with path: {config.path}")
        log.debug(f"Resource parent: {config.parent}")
        self._setup()

    def _getfullpath(self, path: t.Optional[str] = None) -> str:
        """Construct full resource path including parents"""
        parts = []
        current = self._config

        while current:
            if hasattr(current, 'path') and current.path:
                parts.append(current.path)
                log.debug(f"Adding path part: {current.path}")
            current = getattr(current, 'parent', None)
            log.debug(f"Moving to parent: {current}")

        # reverse to get root-> leaf order
        parts.reverse()
        log.debug(f"Path parts after reverse: {parts}")

        # add method path if provided
        if path:
            parts.append(path)
            log.debug(f"Added method path: {path}")

        finalpath = '/'.join(part.strip('/') for part in parts if part)
        log.debug(f"Final constructed path: {finalpath}")
        return finalpath

    def _substitutepathparams(self, path: str, args: tuple, kwargs: dict) -> str:
        """Replace path parameters with values from args or kwargs"""
        if not path:
            return path

        parampattern = r'\{([^}]+)\}'
        params = re.findall(parampattern, path)
        log.debug(f"Path parameters found: {params}")

        if not params:
            return path

        if args:
            log.debug(f"Using positional args for path params: {args}")
            if len(args) != len(params):
                raise ResourceError(
                    f"Expected {len(params)} positional arguments "
                    f"({', '.join(params)}), got {len(args)}"
                )
            for param, arg in zip(params, args):
                path = path.replace(f"{{{param}}}", str(arg))
        else:
            log.debug(f"Using keyword args for path params: {kwargs}")
            for param in params:
                if param not in kwargs:
                    raise ResourceError(f"Missing required path parameter: '{param}'")
                path = path.replace(f"{{{param}}}", str(kwargs.pop(param)))
                log.debug(f"Replaced param {param} in path, now: {path}")

        return path

    def _getbaseurl(self) -> t.Optional[str]:
        """Get the base URL from the client"""
        current = self._config.parent
        log.debug(f"Getting base URL, starting with parent: {current}")

        while current:
            log.debug(f"Checking parent: {current}")
            if hasattr(current, 'baseurl'):
                log.debug(f"Found baseurl: {current.baseurl}")
                return current.baseurl
            current = getattr(current, 'parent', None)
            log.debug(f"Moving to next parent: {current}")

        log.warning("No baseurl found in parent chain")
        return None

    def _buildurl(self, path: str) -> str:
        """Build a full URL from base URL and path"""
        baseurl = self._getbaseurl()
        log.debug(f"Building URL with baseurl: {baseurl} and path: {path}")

        if not baseurl:
            log.warning(f"No baseurl available, returning path only: {path}")
            return path

        # Ensure baseurl has a trailing slash for proper joining
        if not baseurl.endswith('/'):
            baseurl += '/'
            log.debug(f"Added trailing slash to baseurl: {baseurl}")

        # If path starts with slash, remove it for proper joining
        if path.startswith('/'):
            path = path[1:]
            log.debug(f"Removed leading slash from path: {path}")

        # Join paths properly
        fullurl = urljoin(baseurl, path)
        log.debug(f"Final URL after joining: {fullurl}")
        return fullurl

    def _buildrequest(self, cfg: MethodConfig, *args, **kwargs) -> Request:
        """Build a request object for the method"""
        log.debug(f"Building request for method: {cfg.name} with path: {cfg.path}")
        log.debug(f"Args: {args}, Kwargs: {kwargs}")

        # Get the resource path
        resourcepath = self._getfullpath(cfg.path)
        log.debug(f"Full resource path: {resourcepath}")

        # Substitute path parameters
        resourcepath = self._substitutepathparams(resourcepath, args, kwargs)
        log.debug(f"Path after parameter substitution: {resourcepath}")

        # Build the complete URL
        url = self._buildurl(resourcepath)
        log.debug(f"Final URL: {url}")

        # Process payload if available
        if cfg.payload:
            try:
                log.debug(f"Processing payload for method {cfg.method}")
                if cfg.method in (RequestMethod.POST, RequestMethod.PUT, RequestMethod.PATCH):
                   payloaddata = cfg.payload.apply(kwargs)
                   kwargs['json'] = payloaddata
                   log.debug(f"Added JSON payload: {payloaddata}")
                else:
                    kwargs['params'] = cfg.payload.apply(kwargs)
                    log.debug(f"Added query params: {kwargs['params']}")
            except Exception as e:
                log.error(f"Error processing payload: {str(e)}")
                raise ResourceError(f"Error processing payload: {str(e)}")

        # Create and return the request
        reqkwargs = {k:v for k, v in kwargs.items() if not hasattr(cfg, 'payload') or k not in getattr(cfg.payload, 'parameters', {})}
        log.debug(f"Creating request with method: {cfg.method}, url: {url}, kwargs: {reqkwargs}")

        request = Request(
            method=cfg.method,
            url=url,
            **reqkwargs
        )
        log.debug(f"Created request: {request}")
        return request

    def _createmethod(self, cfg: MethodConfig) -> t.Callable:
        """Create a callable method from method configuration"""
        def method(*args, **kwargs):
            log.debug(f"Calling method: {cfg.name}")
            request = self._buildrequest(cfg, *args, **kwargs)
            if cfg.preprocess:
                log.debug(f"Applying preprocessor to request")
                request = cfg.preprocess(request)

            log.debug(f"Sending request: {request}")
            response = self._session.send(request)
            log.debug(f"Received response: status={response.statuscode}")

            if cfg.postprocess:
                log.debug(f"Applying postprocessor to response")
                return cfg.postprocess(response)
            return response
        method.__name__ = cfg.name
        method.__doc__ = cfg.description
        return method

    def _setup(self):
        """Set up methods and child resources"""
        # set up resource methods
        for name, mcfg in self._config.methods.items():
            log.debug(f"Setting up method: {name}")
            if not hasattr(self, name):
                setattr(self, name, self._createmethod(mcfg))

        for name, ccfg in self._config.children.items():
            log.debug(f"Setting up child resource: {name}")
            if not hasattr(self, name):
                ccfg.parent = self._config
                setattr(self, name, Resource(self._session, ccfg))


class ResourceBuilder:
    """Builder for creating Resource instances with fluent configuration"""

    def __init__(self, name: str, path: str = ""):
        """Initialize builder with resource name and path"""
        self._config = ResourceConfig(
            name=name,
            path=(path or name.lower())
        )
        self._session = None
        log.debug(f"Created ResourceBuilder for {name} with path {self._config.path}")

    def path(self, path: str) -> ResourceBuilder:
        """Set the resource path"""
        self._config.path = path
        log.debug(f"Set resource path to: {path}")
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
        log.debug(f"Added method {name} with path {path}")
        return self

    def addchild(self, name: str, child: (ResourceBuilder | ResourceConfig)) -> ResourceBuilder:
        """Add a child resource"""
        if isinstance(child, ResourceBuilder):
            childcfg = child._config
        else:
            childcfg = child

        childcfg.parent = self._config
        self._config.children[name] = childcfg
        log.debug(f"Added child resource: {name}")
        return self

    def session(self, session: Session) -> ResourceBuilder:
        """Set the session to use for this resource"""
        self._session = session
        log.debug(f"Set session for resource")
        return self

    def build(self) -> Resource:
        """Build and return a Resource with the configured options"""
        if not self._session:
            log.error("Cannot build resource: Session is required")
            raise ResourceError("Session is required to build a Resource")
        log.debug(f"Building resource: {self._config.name}")
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
        log.debug(f"Created method decorator for {func.__name__} with path {path}")
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
