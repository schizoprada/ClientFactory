# ~/ClientFactory/src/clientfactory/decorators/client.py
"""
Client Decorators
-------------------
Provides decorators for defining API clients in a declarative style.
"""
from __future__ import annotations
import typing as t
from clientfactory.log import log

from clientfactory.client.base import Client
from clientfactory.declarative import DeclarativeContainer


def clientclass(cls=None, baseurl: t.Optional[str] = None):
    """
    Decorator to mark a class as a client.

    Can be used with or without arguments:
        @client
        class MyClient:
            ...

        @client(baseurl="https://api.example.com")
        class MyClient:
            ...
    """
    metadata = {}
    if baseurl is not None:
        metadata['baseurl'] = baseurl

    def decorator(cls):
        baseattrs = {}
        for base in cls.__bases__:
            if (base != Client) and (base != DeclarativeContainer):
                for name, value in vars(base).items():
                    if (
                        not name.startswith('_')
                        and not callable(value)
                        and not isinstance(value, type)
                        and not isinstance(value, property)
                    ):
                        baseattrs[name] = value
        # If already a Client, just update metadata
        if isinstance(cls, type) and issubclass(cls, Client):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
                if k == 'baseurl':
                    cls.baseurl = v
            # apply base attributes
            for k, v in baseattrs.items():
                if not hasattr(cls, k):
                    setattr(cls, k, v)
                    cls.setmetadata(k, v)
            return cls

        # Create new namespace with baseurl if provided
        namespace = dict(cls.__dict__)
        namespace.update(baseattrs)

        if baseurl is not None:
            namespace['baseurl'] = baseurl

        # Determine proper bases
        if issubclass(cls, DeclarativeContainer):
            bases = tuple(b if b != DeclarativeContainer else Client for b in cls.__bases__)
        else:
            bases = (Client,) + cls.__bases__

        # Create new class - it will automatically get DeclarativeMeta through Client
        newcls = type(cls.__name__, bases, namespace)

        # Apply metadata after class creation
        for k, v in metadata.items():
            newcls.setmetadata(k, v)

        for k, v in baseattrs.items():
            if not newcls.hasmetadata(k):
                newcls.setmetadata(k, v)

        log.debug(f"client: converted ({cls.__name__}) to declarative client")
        return newcls

    return decorator if cls is None else decorator(cls)
