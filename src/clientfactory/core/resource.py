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
from urllib.parse import urljoin

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
        self._setup()

    def _getfullpath(self, path: t.Optional[str] = None) -> str:
        """Construct full resource path including parents"""
        parts = []
        current = self._config

        while current:
            if hasattr(current, 'path') and current.path:
                parts.append(current.path)
            current = getattr(current, 'parent', None)

        # reverse to get root-> leaf order
        parts.reverse()

        # add method path if provided
        if path:
            parts.append(path)
        return '/'.join(part.strip('/') for part in parts if part)

    def _substitutepathparams(self, path: str, args: tuple, kwargs: dict) -> str:
        """Replace path parameters with values from args or kwargs"""
        if not path:
            return path

        parampattern = r'\{([^}]+)\}'
        params = re.findall(parampattern, path)

        if not params:
            return path

        if args:
            if len(args) != len(params):
                raise ResourceError(
                    f"Expected {len(params)} positional arguments"
                    f"({', '.join(params)}), got {len(args)}"
                )
            for param, arg in zip(params, args):
                path = path.replace(f"{{{param}}}", str(arg))
        else:
            for param in params:
                if param not in kwargs:
                    raise ResourceError(f"Missing required path parameter: '{param}'")
                path = path.replace(f"{{{param}}}", str(kwargs.pop(param)))

        return path


    def _buildrequest(self, cfg: MethodConfig, *args, **kwargs) -> Request:
        path = self._getfullpath(cfg.path)
        url = self._substitutepathparams(path, args, kwargs)

        if cfg.payload:
            try:
                if cfg.method in (RequestMethod.POST, RequestMethod.PUT, RequestMethod.PATCH):
                   payloaddata = cfg.payload.apply(kwargs)
                   kwargs['json'] = payloaddata
                else:
                    kwargs['params'] = cfg.payload.apply(kwargs)
            except Exception as e:
                raise ResourceError(f"Error processing payload: {str(e)}")

        return Request(
            method=cfg.method,
            url=url,
            **{k:v for k, v in kwargs.items() if k not in getattr(cfg.payload, 'parameters', {})}
        )

    def _createmethod(self, cfg: MethodConfig) -> t.Callable:
        """Create a callable method from method configuration"""
        def method(*args, **kwargs):
            request = self._buildrequest(cfg, *args, **kwargs)
            if cfg.preprocess:
                request = cfg.preprocess(request)
                response = self._session.send(request)
                if cfg.postprocess:
                    return cfg.postprocess(response)
                return response
        method.__name__ = cfg.name
        method.__doc__ = cfg.description
        return method

    def _setup(self):
        """Set up methods and child resources"""
        # set up resource methods
        for name, mcfg in self._config.methods.items():
            if not hasattr(self, name):
                setattr(self, name, self._createmethod(mcfg))

        for name, ccfg in self._config.children.items():
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

    def path(self, path: str) -> ResourceBuilder:
        """Set the resource path"""
        self._config.path = path
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
            description=description
        )
        return self

    def addchild(self, name: str, child: (ResourceBuilder | ResourceConfig)) -> ResourceBuilder:
        """Add a child resource"""
        if isinstance(child, ResourceBuilder):
            childcfg = child._config
        else:
            childcfg = child

        childcfg.parent = self._config
        self._config.children[name] = childcfg
        return self

    def session(self, session: Session) -> ResourceBuilder:
        """Set the session to use for this resource"""
        self._session = session
        return self

    def build(self) -> Resource:
        """Build and return a Resource with the configured options"""
        if not self._session:
            raise ResourceError("Session is required to build a Resource")
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
