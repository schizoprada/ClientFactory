# ~/ClientFactory/src/clientfactory/client/base.py
"""
Client Class
------------
This module defines the core Client class that serves as the main interface for interacting with APIs.
It manages resources, authentication, and session handling.
"""

from __future__ import annotations
import inspect, typing as t
from dataclasses import dataclass, field
from clientfactory.log import log

from clientfactory.core import (
    Session, SessionConfig, SessionBuilder,
    Resource, ResourceConfig, Request, RequestMethod
)
from clientfactory.auth import BaseAuth
from clientfactory.client.config import ClientConfig
from clientfactory.declarative import DeclarativeContainer


T = t.TypeVar('T', bound='Resource')


class ClientError(Exception):
    """Base exception raised for client related errors."""
    pass

class Client(DeclarativeContainer):
    """
    Base client class for API interaction.

    The Client class serves as a container for resources and manages authentication and session configuration.
    It can be used directly or via a ClientBuilder
    """
    __declarativetype__ = 'client'
    baseurl: str = ""
    auth: t.Optional[t.Union[BaseAuth, t.Type[BaseAuth]]] = None
    config: t.Optional[ClientConfig] = None

    __resources__: t.ClassVar[t.Dict[str, t.Type[Resource]]] = {}

    def __init__(self, baseurl: t.Optional[str] = None, auth: t.Optional[BaseAuth] = None, config: t.Optional[ClientConfig] = None):
        """Initialize a new client instance"""
        from clientfactory.utils.internal import attributes

        log.debug(f"Initializing client with baseurl: {baseurl}")
        sources = [self, self.__class__]

        # Strategic logs for auth resolution
        log.info(f"DEBUGGING CLIENT INIT - Sources for auth resolution: {sources}")
        log.info(f"DEBUGGING CLIENT INIT - Class variables: {[k for k in dir(self.__class__) if not k.startswith('_')]}")
        log.info(f"DEBUGGING CLIENT INIT - Class auth attr: {getattr(self.__class__, 'auth', None)}")
        log.info(f"DEBUGGING CLIENT INIT - Class metadata: {getattr(self.__class__, '__metadata__', {}).get('auth', None)}")
        log.info(f"DEBUGGING CLIENT INIT - Class components: {getattr(self.__class__, '__metadata__', {}).get('components', {}).get('auth', None)}")

        authattr = auth or attributes.resolve('auth', sources)
        log.info(f"DEBUGGING CLIENT INIT - AUTH ATTR: {authattr}")
        if (authattr is not None) and inspect.isclass(authattr):
            log.info(f"DEBUGGING CLIENT INIT - AUTH IS A CLASS - INSTANTIATING: {authattr.__class__.__name__}")
            self._auth = authattr()
            log.info(f"DEBUGGING CLIENT INIT - AUTH INSTANTIATED AND SET: {self._auth.__class__.__name__}")
        else:
            log.info(f"DEBUGGING CLIENT INIT - AUTH IS EITHER NONE OR INSTANTIATED - SETTING")
            self._auth = authattr



        self._config = (config or ClientConfig(baseurl=(baseurl or self.baseurl)))
        log.debug(f"Initial config baseurl: {self._config.baseurl}")

        if (baseurl is not None):
            self.baseurl = baseurl
            log.debug(f"Set baseurl from parameter: {self.baseurl}")
        elif config is not None and config.baseurl:
            self.baseurl = config.baseurl
            log.debug(f"Set baseurl from config: {self.baseurl}")

        # Make sure _config.baseurl is consistent with self.baseurl
        if self._config.baseurl != self.baseurl:
            log.debug(f"Updating config.baseurl to match self.baseurl: {self.baseurl}")
            self._config.baseurl = self.baseurl

        log.debug(f"Final baseurl: {self.baseurl}")
        log.debug(f"Final config.baseurl: {self._config.baseurl}")

        instancesession = attributes.resolve('session', sources)
        if instancesession is not None:
            if inspect.isclass(instancesession):
                self._session = instancesession(auth=self._auth)
                log.info(f"DEBUGGING CLIENT INIT - CREATED SESSION FROM CLASS ATTRIBUTE WITH AUTH: {self._auth}")
                log.info(f"DEBUGGING CLIENT INIT - SESSION AUTH CHECK: {self._session.auth}")
            else:
                self._session = instancesession
                if hasattr(self._session, 'auth') and self._auth is not None:
                    self._session.auth = self._auth
                    log.debug(f"APPLIED AUTH TO EXISTING SESSION")
        else:
            self._session = self._createsession()
            log.debug("CREATED DEFAULT SESSION")
        self._resources: dict[str, Resource] = {}
        self._discoverresources()

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.__resources__ = {}

        dictitems = list(cls.__dict__.items())

        for name, value in dictitems:
            if (
                inspect.isclass(value) and
                hasattr(value, '_resourceconfig') and
                hasattr(value, '_resourcetype')
            ):
                # register for type check
                resourcetype = value._resourcetype
                cls.__resources__[name.lower()] = resourcetype


                # add type annotation to class
                if not hasattr(cls, '__annotations__'):
                    cls.__annotations__ = {}
                cls.__annotations__[name.lower()] = resourcetype

    def __getattr__(self, name: str) -> t.Any:
        rsrcs = self.__dict__.get('_resources')
        if rsrcs and name in rsrcs:
            return rsrcs[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


    def _createsession(self) -> Session:
        """Create a new session"""
        log.debug("Creating session")
        if (customsession:=getattr(self, 'session', None)) is not None:
            log.info(f"DEBUGGING SESSION CREATION - Using custom session: {customsession}")
            log.info(f"DEBUGGING SESSION CREATION - Auth to pass: {self._auth}")
            if isinstance(customsession, type):
                log.info(f"DEBUGGING SESSION CREATION - Session is a class")
                log.info(f"DEBUGGING SESSION CREATION - Session class attrs: {[k for k in dir(customsession) if not k.startswith('_')]}")

                # Create a session config that includes any cookies or headers from the client config
                sessionconfig = SessionConfig(
                    headers=self._config.headers,
                    cookies=self._config.cookies,
                    verify=self._config.verifyssl
                )

                # Create the session instance with auth and config
                instance = customsession(auth=self._auth, config=sessionconfig)

                log.info(f"DEBUGGING SESSION CREATION - Instantiated session: {instance}")
                log.info(f"DEBUGGING SESSION CREATION - Session auth after init: {getattr(instance, 'auth', None)}")
                log.info(f"DEBUGGING SESSION CREATION - Session headers: {instance._session.headers if hasattr(instance, '_session') else 'No _session attribute'}")

                return instance
            log.info(f"DEBUGGING SESSION CREATION - Using existing session instance")
            return customsession

        # Default session creation if no custom session is provided
        cfg = SessionConfig(
            headers=self._config.headers,
            cookies=self._config.cookies,
            verify=self._config.verifyssl
        )
        return Session(
            config=cfg,
            auth=self._auth
        )

    def _initresource(self, cls: t.Type, config: ResourceConfig) -> Resource:
        """Initialize a resource instance"""
        log.debug(f"Initializing resource: {config.name} with path: {config.path}")
        log.debug(f"Setting resource parent to client")

        # Set parent to self to make baseurl available
        config.parent = self
        log.debug(f"Resource parent set to: {config.parent}")

        resource = Resource(
            session=self._session,
            config=config
        )
        log.debug(f"Resource initialized: {resource}")
        return resource

    def _discoverresources(self) -> None:
        """
        Discover resources defined as nested classes.

        This method looks for classes with a '_resourceconfig' attribute
        that indicates they've been decorated with '@resource'.
        """
        log.debug("Discovering resources")
        for name, cls in inspect.getmembers(self.__class__, lambda x: inspect.isclass(x) and hasattr(x, '_resourceconfig')):
            log.debug(f"Found resource class: {name}")
            if (resourcetype:=getattr(cls, '_resourcetype', None)):
                log.debug(f"Using specialized resource type: {resourcetype.__name__}")
                cls._resourceconfig.parent = self

                attributes = {}
                for attrname in dir(cls):
                    if not attrname.startswith('_'):
                        attrvalue = getattr(cls, attrname)
                        if not callable(attrvalue):
                            attributes[attrname] = attrvalue

                resource = resourcetype(self._session, cls._resourceconfig, attributes=attributes)
                self._resources[cls.__name__.lower()] = resource
                setattr(self, cls.__name__.lower(), resource)
            else:
                self.register(cls)

    def register(self, resourcecls: t.Type) -> None:
        """Manually register a resource class"""
        log.debug(f"Registering resource class: {resourcecls.__name__}")

        if not hasattr(resourcecls, '_resourceconfig'):
            log.error(f"Class {resourcecls.__name__} is not a '@resource'")
            raise ClientError(f"Class {resourcecls.__name__} is not a '@resource'")

        config = resourcecls._resourceconfig
        log.debug(f"Resource config: {config.name}, path: {config.path}")

        # Explicitly set parent to self so resource can access client attributes
        config.parent = self
        log.debug(f"Set resource parent to client: {config.parent}")

        name = resourcecls.__name__.lower()
        log.debug(f"Resource attribute name: {name}")

        resource = self._initresource(resourcecls, config)
        self._resources[name] = resource
        setattr(self, name, resource)
        log.debug(f"Resource registered and bound to attribute: {name}")

    def close(self) -> None:
        """Close the client and release resources"""
        log.debug("Closing client")
        self._session.close()

    def __enter__(self) -> Client:
        """Enter context manager"""
        log.debug("Entering client context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager and close the client"""
        log.debug("Exiting client context")
        self.close()

    @classmethod
    def _processclassattributes(cls) -> None:
        """
        Process client-specific class attributes.

        Extends the container implementation to extract client-specific configurations and discover resources.
        """
        super()._processclassattributes()

        if ('baseurl' not in cls.__metadata__) and (hasattr(cls, 'baseurl')):
            cls.__metadata__['baseurl'] = cls.baseurl
            log.debug(f"DeclarativeClient: extracted baseurl ({cls.baseurl}) from: {cls.__name__}")

        if 'resources' not in cls.__metadata__:
            cls.__metadata__['resources'] = {}

        for name, value in vars(cls).items():
            if name.startswith('__') and name.endswith('__'):
                continue

            if inspect.isclass(value) and issubclass(value, Resource):
                resourcename = value.__metadata__.get('name', name.lower())
                cls.__metadata__['resources'][resourcename] = value
                log.debug(f"DeclarativeClient: found resource ({resourcename}) on: {cls.__name__}")

                value.setmetadata('parent', cls)

    @classmethod
    def getresources(cls) -> dict:
        return cls.__metadata__.get('resources', {})

    @classmethod
    def getbaseurl(cls) -> str:
        return cls.__metadata__.get('baseurl', '')
