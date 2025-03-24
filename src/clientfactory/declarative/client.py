# ~/ClientFactory/src/clientfactory/declarative/client.py
"""
Declarative Clients
-------------------
Client-specific declarative components.
Provides classes and decorators for defineing API clients in a declarative style.
"""
from __future__ import annotations
import inspect, typing as t
from loguru import logger as log

from clientfactory.declarative.base import DeclarativeContainer
from clientfactory.declarative.resource import DeclarativeResource

class DeclarativeClient(DeclarativeContainer):
    """
    Base class for declarative API clients.

    Enhances DeclarativeContainer with client-specific functionality for managing resources and configuration.
    """

    __declarativetype__ = 'client'

    baseurl: str = ""

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

            if inspect.isclass(value) and issubclass(value, DeclarativeResource):
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


def client(cls=None, baseurl: t.Optional[str] = None):
    """
    """
    metadata = {}
    if baseurl is not None:
        metadata['baseurl'] = baseurl

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, DeclarativeClient):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
            if baseurl is not None:
                cls.baseurl = baseurl
            return cls

        if issubclass(cls, DeclarativeContainer):
            bases = tuple(b if b != DeclarativeContainer else DeclarativeClient for b in cls.__bases__)
        else:
            bases = (DeclarativeClient,) + cls.__bases__

        newcls = type(cls.__name__, bases, dict(cls.__dict__))

        for k, v in metadata.items():
            newcls.setmetadata(k, v)
            if (k == 'baseurl') and (baseurl is not None):
                newcls.baseurl = baseurl

        log.debug(f"client: converted ({cls.__name__}) to declarative client")
        return newcls

    if cls is None:
        return decorator
    return decorator(cls)
