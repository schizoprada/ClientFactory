# ~/clientfactory/resources/base.py
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field, fields
import inspect
from clientfactory.utils.request import Request, RequestMethod
from clientfactory.session.base import BaseSession
from clientfactory.transformers.base import Transform, TransformPipeline
from loguru import logger as log

@dataclass
class ResourceConfig:
    """Configuration for a resource endpoint"""
    name: str
    path: str
    methods: dict = field(default_factory=dict)  # name -> method config
    children: dict = field(default_factory=dict)  # name -> resource config
    baseurl: t.Optional[str] = None # for resources belonging to the main Client class that utilize different URLs, e.g. media servers, etc.
    parent: t.Optional[('ResourceConfig' | 'ClientConfig')] = None
    transforms: t.List[Transform] = field(default_factory=list)
    pipeline: t.Optional[TransformPipeline] = None

@dataclass
class MethodConfig:
    """Configuration for a resource method"""
    name: str
    method: RequestMethod
    path: t.Optional[str] = None
    preprocess: t.Optional[t.Callable] = None
    postprocess: t.Optional[t.Callable] = None

class Resource:
    """
    Base resource class that handles endpoint operations.
    Can be nested to represent API hierarchy.
    """
    def __init__(self,
                 session: BaseSession,
                 config: ResourceConfig,
                 resourcecls:t.Optional[t.Type]=None,
                 clientconfig:t.Optional["ClientConfig"]=None,
                 pipeline: t.Optional[TransformPipeline] = None
                ):
        self._session = session
        self._config = config
        self._resourcecls = resourcecls # store original class
        if clientconfig and not self._config.parent:
            self._config.parent = clientconfig

        if pipeline:
            self._config.pipeline = pipeline
        elif self._config.transforms:
            self._config.pipeline = TransformPipeline(self._config.transforms)
        self.__setup__()

    def transform(self, value:t.Any) -> t.Any:
        if self._config.pipeline:
            return self._config.pipeline(value)
        return value

    def __setup__(self):
        """Setup methods and child resources"""
        def methods():
            """Set up resource methods"""
            for name, methodcfg in self._config.methods.items():
                if not hasattr(self, name):
                    setattr(self, name, self.__methodize__(methodcfg))

        def children():
            """Set up child resources"""
            for name, childcfg in self._config.children.items():
                if not hasattr(self, name):
                    setattr(self, name, Resource(self._session, childcfg))

        methods()
        children()

    def __methodize__(self, cfg: MethodConfig) -> t.Callable:
        """Create a callable method from method configuration"""
        def method(*args, **kwargs):
            # transform kwargs if pipeline exists
            transformed = self.transform(kwargs)
            # Build request
            # For non-endpoint methods, just execute the original function
            if cfg.method == RequestMethod.NA:
                log.debug(f"resources.base.resource.__methodize__ | executing non-endpoint method: {cfg.name}")
                if not self._resourcecls:
                    raise ValueError(f"No resource class available for method: {cfg.name}")
                return getattr(self._resourcecls, cfg.name)(self, *args, **transformed)
            request = self.__build__(cfg, *args, **transformed)
            log.debug(f"resources.base.resource.__methodize__ | built: request[{request}]")

            # store original kwargs in request for preprocessors
            request.kwargs = kwargs
            request.transformed = transformed

            # Apply preprocessing if configured
            if cfg.preprocess:
                log.debug(f"resources.base.resource.__methodize__ | found: preprocessor[{cfg.preprocess}]")
                #handle both instance method and standalone function
                if hasattr(cfg.preprocess, "__get__"): # is instance method
                    log.debug(f"resources.base.resource.__methodize__ | binding preprocessor to instance")
                    request = cfg.preprocess.__get__(self, self.__class__)(request)
                else: # is standalone function
                    request = cfg.preprocess(request)
                log.debug(f"resources.base.resource.__methodize__ | preprocessed: request[{request}]")

            # Apply auth before executing
            if self._session.auth: # dont confuse the Base Session with the Session Config
                log.debug(f"resources.base.resource.__methodize__ | applying auth")
                request = self._session.auth.prepare(request)
                log.debug(f"resources.base.resource.__methodize__ | auth applied: request[{request}]")

            # Execute request
            response = self._session.send(request)
            log.debug(f"resources.base.resource.__methodize__ | response[{response}]")

            # Apply postprocessing if configured
            if cfg.postprocess:
                log.debug(f"resources.base.resource.__methodize__ | found: postprocessor[{cfg.postprocess}]")
                # handle both instance method and standalone function
                if hasattr(cfg.postprocess, "__get__"): # is instance method
                    log.debug(f"resources.base.resource.__methodize__ | binding postprocessor to instance")
                    response = cfg.postprocess.__get__(self, self.__class__)(response)  # Fixed: assign to response
                else: # is standalone function
                    response = cfg.postprocess(response)
                log.debug(f"resources.base.resource.__methodize__ | postprocessed: response[{response}]")

            return response

        # Set method metadata
        method.__name__ = cfg.name
        method.__doc__ = getattr(cfg, 'doc', None)

        return method

    def __build__(self, cfg: MethodConfig, *args, **kwargs) -> Request:
        """Build request for method invocation"""
        # Get full resource path
        path = self.__fullpath__(cfg.path)
        if not self._config.parent:
            raise ValueError(f"resources.base.resource.__build__ | resource not properly initialized with client configuration")
        baseurl = self._config.baseurl or self._config.parent.baseurl #
        url = f"{baseurl.rstrip('/')}/{path.lstrip('/')}"
        log.debug(f"resources.base.resource.__build__ | built url[{url}]")
        # Extract path parameters from template
        if cfg.path:
            # Find all {param} in path
            pathparams = [
                param.strip('{}')
                for param in url.split('/')
                if param.startswith('{') and param.endswith('}')
            ]

            # Handle positional args
            if args:
                if len(args) != len(pathparams):
                    raise ValueError(
                        f"Expected {len(pathparams)} positional arguments "
                        f"({', '.join(pathparams)}), got {len(args)}"
                    )
                # Convert positional to named
                pathkwargs = dict(zip(pathparams, args))
                url = url.format(**pathkwargs)

            # Handle named args - extract path params from kwargs
            else:
                pathkwargs = {}
                for param in pathparams:
                    if param not in kwargs:
                        raise ValueError(f"Missing required path parameter: {param}")
                    pathkwargs[param] = kwargs.pop(param)  # Remove from kwargs after use
                url = url.format(**pathkwargs)

        # get valid Request constructor fields
        RequestFields = {field.name for field in fields(Request)}
        requestkwargs = {k:v for k, v in kwargs.items() if k in RequestFields}
        methodkwargs = {k:v for k, v in kwargs.items() if k not in RequestFields}
        requestkwargs['kwargs'] = methodkwargs

        return Request(method=cfg.method, url=url, **requestkwargs)

    def __fullpath__(self, methodpath: t.Optional[str]=None) -> str:
        """Construct full resource path including parents"""
        # Collect path components from resource chain
        parts = []
        current = self._config

        while current and hasattr(current, 'path'): # stop if we hit ClientConfig
            if current.path:
                parts.append(current.path)
            current = current.parent

        # Reverse to get root->leaf order
        parts.reverse()

        # Add method path if provided
        if methodpath:
            parts.append(methodpath)

        # Combine and normalize
        return '/'.join(p.strip('/') for p in parts if p)


    def __matmul__(self, method: t.Union[str, t.Callable, t.Tuple[t.Callable, t.Union[str, RequestMethod]]]) -> 'Resource':
        """
        Register a new method using the @ operator

        Usage:
            resource @ my_method  # defaults to GET
            resource @ "method_name" @ my_method
            resource @ (my_method, 'GET')  # or 'get', 'POST', etc
            resource @ (my_method, RequestMethod.POST)
        """
        if isinstance(method, str):
            self._pendingmethodname = method
            return self

        # Get method name (either pending or from function)
        if hasattr(self, '_pendingmethodname'):
            methodname = self._pendingmethodname
            delattr(self, '_pendingmethodname')
        else:
            if isinstance(method, tuple):
                func = method[0]
            else:
                func = method
            methodname = func.__name__

        # Handle method tuple case (method with HTTP method specification)
        if isinstance(method, tuple):
            func, methodspec = method
            # Convert method specification
            if isinstance(methodspec, str):
                requestmethod = RequestMethod(methodspec.upper())
            elif isinstance(methodspec, RequestMethod):
                requestmethod = methodspec
            else:
                raise ValueError(f"Invalid method specification: {methodspec}")

            # Create method config
            from clientfactory.resources.decorators import MethodConfig
            methodcfg = MethodConfig(
                name=methodname,
                method=requestmethod,
                path=getattr(func, '_methodcfg', None).path if hasattr(func, '_methodcfg') else None,
                preprocess=getattr(func, '_preprocess', None),
                postprocess=getattr(func, '_postprocess', None)
            )
        else:
            func = method
            # Use existing config or create default GET config
            methodcfg = getattr(func, '_methodcfg', None)
            if not methodcfg:
                from clientfactory.resources.decorators import MethodConfig
                methodcfg = MethodConfig(
                    name=methodname,
                    method=RequestMethod.GET,
                    preprocess=getattr(func, '_preprocess', None),
                    postprocess=getattr(func, '_postprocess', None)
                )

        # Create a wrapper function that will have our method config
        def wrapper(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        # Transfer the method config
        wrapper._methodcfg = methodcfg

        # Bind the wrapper
        boundmethod = wrapper.__get__(self, self.__class__)

        # Register both path-based and method name attributes if decorated
        if methodcfg.path:
            pathname = methodcfg.path.split('/')[-1]
            setattr(self, pathname, boundmethod)

        # Always set the original method name
        setattr(self, methodname, boundmethod)

        return self

    def __new__(cls, *args, **kwargs):
        if (resourcecls:=kwargs.get('resourcecls')) and hasattr(resourcecls, '__resourceclass__'):
            return object.__new__(resourcecls.__resourceclass__)
        return object.__new__(cls)
