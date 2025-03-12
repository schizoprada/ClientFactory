# ~/clientfactory/client.py
from __future__ import annotations
import typing as t
from inspect import getmembers, isclass
from dataclasses import dataclass, field

from clientfactory.auth.base import BaseAuth, NoAuth
from clientfactory.session.base import BaseSession, SessionConfig
from clientfactory.resources.base import Resource, ResourceConfig
from clientfactory.utils.request import RequestConfig, RequestMethod
from clientfactory.transformers.base import Transform, TransformPipeline, Transformer

from loguru import logger as log

@dataclass
class ClientConfig:
    """Configuration for client behavior"""
    baseurl: str = ""
    request: RequestConfig = field(default_factory=RequestConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    transformer: Transformer = field(default_factory=Transformer)

class Client:
    """
    Base client class for API interaction.
    Supports both class-based and builder-based initialization.

    Class-based usage:
        class GitHub(Client):
            baseurl = "https://api.github.com"
            auth = ApiKeyAuth.header("token", prefix="Bearer")

            @resource
            class Repos:
                @get("user/repos")
                def list_repos(self): pass

    Builder usage:
        github = ClientBuilder()\\
            .base_url("https://api.github.com")\\
            .auth(ApiKeyAuth.header("token"))\\
            .build()
    """

    baseurl: str = ""
    auth: t.Optional[BaseAuth] = None
    config: t.Optional[ClientConfig] = None
    transformer: t.Optional[Transformer] = None

    def __init__(self,
                 baseurl: t.Optional[str] = None,
                 auth: t.Optional[BaseAuth] = None,
                 config: t.Optional[ClientConfig] = None,
                 transformer: t.Optional[Transformer] = None
                ):
        """
        Initialize client with optional overrides.
        Class attributes can be overridden by constructor args.
        """
        # Allow constructor args to override class attributes
        self.baseurl = baseurl or self.baseurl
        self.auth = auth or self.auth or NoAuth()
        self.config = config or self.config or ClientConfig(baseurl=self.baseurl)
        self.transformer = transformer or self.transformer or self.config.transformer
        # Ensure baseurl consistency
        if self.baseurl and self.baseurl != self.config.baseurl:
            self.config.baseurl = self.baseurl

        self._resources: dict[str, Resource] = {}
        self._pipelines: dict[str, TransformPipeline] = {}

        # Setup order matters:
        # 1. Auth may need session
        # 2. Resources need both auth and session
        self.__setup__()

    def __setup__(self):
        def __transformer(self):
            """Initialize transformer pipelines"""
            log.debug(f"client.Client.__setup__.__transformer | setting up transform pipelines")
            for name, pipeline in getmembers(self.__class__, lambda x: isinstance(x, TransformPipeline)):
                log.debug(f"client.Client.__setup__.__transformer | found pipeline: {name}")
                self._pipelines[name] = pipeline
        def __session(self):
            """Initialize session"""
            log.debug(f"client.Client._setup_session | creating session with config: {self.config.session}")
            self._session = BaseSession(config=self.config.session, auth=self.auth)
        def __auth(self):
            """Initialize authentication"""
            log.debug(f"client.Client._setup_auth | initializing auth: {self.auth}")
            if not self.auth.isauthenticated:
                self.auth.authenticate()
        def __resources(self):
            """
            Discover and initialize resources.
            Looks for nested classes with @resource decorator.
            """
            log.debug("client.Client._setup_resources | discovering resources")

            # Get all nested classes with _resourcecfg
            for name, cls in getmembers(self.__class__,
                lambda x: isclass(x) and hasattr(x, '_resourcecfg')):
                log.debug(f"client.Client._setup_resources | found resource: {name}")

                # resource-level transforms
                pipeline = None
                if hasattr(cls, 'transforms'):
                    pipeline = TransformPipeline(cls.transforms)


                # Initialize resource with our session
                resource = Resource(
                    session=self._session,
                    config=cls._resourcecfg,
                    resourcecls=cls,  # pass the original class
                    clientconfig=self.config, # pass client config
                    pipeline=pipeline
                )

                # Store and attach to client
                self._resources[name.lower()] = resource
                setattr(self, name.lower(), resource)
        __session(self)
        __auth(self)
        __transformer(self)
        __resources(self)

    def register(self, resource_cls: t.Type) -> None:
        """
        Manually register a resource class.
        Useful for builder pattern or dynamic registration.
        """
        if not hasattr(resource_cls, '_resourcecfg'):
            raise ValueError(
                f"Class {resource_cls.__name__} is not a @resource"
            )

        name = resource_cls.__name__.lower()
        log.debug(f"client.Client.register | registering resource: {name}")

        resource = Resource(
            session=self._session,
            config=resource_cls._resourcecfg,
            clientconfig=self.config
        )

        self._resources[name] = resource
        setattr(self, name, resource)

    def close(self):
        """Cleanup client resources"""
        self._session.close()

    def transform(self, name:str, value:t.Any) -> t.Any:
        """Execute a named transform pipeline"""
        if name not in self._pipelines:
            raise KeyError(f"Transform pipeline '{name}' not found")
        return self._pipelines[name](value)

    def addpipeline(self, name:str, pipeline:TransformPipeline) -> None:
        """Add a transform pipeline"""
        self._pipelines[name] = pipeline

    def getpipeline(self, name:str) -> t.Optional[TransformPipeline]:
        return self._pipelines.get(name, None)


    def __enter__(self) -> Client:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __matmul__(self, target: t.Union[
        str,                    # For method naming
        t.Type,                 # For resource registration
        t.Callable,             # For method registration
        t.Tuple[t.Union[t.Type, t.Callable], t.Union[str, RequestMethod]]  # For method with HTTP method
    ]) -> 'Client':
        """
        Register methods or resources using the @ operator

        Usage:
            # Method registration
            client @ my_method  # defaults to GET
            client @ "custom_name" @ my_method
            client @ (my_method, 'POST')
            client @ (my_method, RequestMethod.PUT)

            # Resource registration
            client @ MyResource
            client @ "custom_name" @ MyResource
        """
        # Handle string case for naming
        if isinstance(target, str):
            self._pendingname = target
            return self

        name = getattr(self, '_pendingname', None)
        if hasattr(self, '_pendingname'):
            delattr(self, '_pendingname')

        # Handle resource class case
        if isinstance(target, type):
            if not hasattr(target, '_resourcecfg'):
                from clientfactory.resources.decorators import resource
                target = resource(target)

            # Use pending name or class name
            resource_name = name or target.__name__.lower()

            # Create resource instance
            resource = Resource(
                session=self._session,
                config=target._resourcecfg
            )

            # Register resource
            if not hasattr(self, '_resources'):
                self._resources = {}
            self._resources[resource_name] = resource
            setattr(self, resource_name, resource)
            return self

        # Handle method case
        if isinstance(target, tuple):
            func, method_spec = target
            # Convert method specification
            if isinstance(method_spec, str):
                method = RequestMethod(method_spec.upper())
            elif isinstance(method_spec, RequestMethod):
                method = method_spec
            else:
                raise ValueError(f"Invalid method specification: {method_spec}")
        else:
            func = target
            method = RequestMethod.GET

        # Use pending name or function name
        method_name = name or func.__name__

        # Create method config
        from clientfactory.resources.decorators import MethodConfig
        if not hasattr(func, '_methodcfg'):
            func._methodcfg = MethodConfig(
                name=method_name,
                method=method
            )

        # Bind the method to the client
        bound_method = func.__get__(self, self.__class__)
        setattr(self, method_name, bound_method)

        return self
