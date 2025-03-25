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
from loguru import logger as log

from clientfactory.core import (
    Session, SessionConfig, SessionBuilder,
    Resource, ResourceConfig, Request, RequestMethod
)
from clientfactory.auth import BaseAuth
from clientfactory.client.config import ClientConfig
from clientfactory.declarative import DeclarativeContainer


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
    auth: t.Optional[BaseAuth] = None
    config: t.Optional[ClientConfig] = None

    def __init__(self, baseurl: t.Optional[str] = None, auth: t.Optional[BaseAuth] = None, config: t.Optional[ClientConfig] = None):
        """Initialize a new client instance"""
        log.debug(f"Initializing client with baseurl: {baseurl}")

        self._auth = auth
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

        self._session = self._createsession()
        self._resources: dict[str, Resource] = {}
        self._discoverresources()

    def _createsession(self) -> Session:
        """Create a new session"""
        log.debug("Creating session")
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
