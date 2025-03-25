# ~/ClientFactory/src/clientfactory/decorators/client.py
"""
Client Decorators
-------------------
Provides decorators for defining API clients in a declarative style.
"""
from __future__ import annotations
import typing as t
from loguru import logger as log

from clientfactory.client.base import Client
from clientfactory.declarative import DeclarativeContainer


def client(cls=None, baseurl: t.Optional[str] = None):
    """
    """
    metadata = {}
    if baseurl is not None:
        metadata['baseurl'] = baseurl

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, Client):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
            if baseurl is not None:
                cls.baseurl = baseurl
            return cls

        if issubclass(cls, DeclarativeContainer):
            bases = tuple(b if b != DeclarativeContainer else Client for b in cls.__bases__)
        else:
            bases = (Client,) + cls.__bases__

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
