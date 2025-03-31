# ~/ClientFactory/src/clientfactory/declarative/decorators.py
"""
Declarative Decorators
----------------------
Decorators for declarative API definition.
Provides decorators for marking classes and methods with declarative attributes.
"""
from __future__ import annotations
import typing as t, functools as fn
from clientfactory.log import log

from clientfactory.declarative.base import DeclarativeComponent, DeclarativeContainer

def declarative(cls=None, *, metadata: t.Optional[dict] = None):
    """
    Decorator to mark a class as declarative.

    Ensures that a class is a subclass of DeclarativeComponent and applies metadata if provided.
    """

    metadata = (metadata or {})

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, DeclarativeComponent):
            # already declarative, update metdata
            for k, v in metadata.items():
                cls.setmetadata(k, v)
            return cls

        bases = (DeclarativeComponent, ) + cls.__bases__
        newcls = type(cls.__name__, bases, dict(cls.__dict__))

        for k, v in metadata.items():
            newcls.setmetadata(k, v)

        #log.debug(f"declarative: converted ({cls.__name__}) to declarative component")
        return newcls

    if cls is None:
        return decorator
    return decorator(cls)


def declarativemethod(method=None, **metadata):
    """
    Decorator to mark a method as declarative.

    Adds metadata to the method to be processed by DeclarativeContainer during class initialization.
    """
    def decorator(func):
        func.__declarativemethod__ = True

        if not hasattr(func, '__metadata__'):
            func.__metadata__ = {}

        func.__metadata__.update(metadata)

        return func

    if method is None:
        return decorator
    return decorator(method)


def container(cls=None, *, metadata: t.Optional[dict] = None):
    """
    Decorator to mark a class as a declarative container.

    Ensures that a class is a subclass of DeclarativeContainer and applies metadata if provided.
    """
    metadata = (metadata or {})

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, DeclarativeContainer):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
            return cls

        # not a container, create a new class with DeclarativeContainer as base
        if issubclass(cls, DeclarativeComponent):
            # already declarative but not a container
            bases = tuple(b if b!=DeclarativeComponent else DeclarativeContainer for b in cls.__bases__)
        else:
            # not declarative at all
            bases = (DeclarativeContainer, ) + cls.__bases__

        newcls = type(cls.__name__, bases, dict(cls.__dict__))

        for k, v in metadata.items():
            newcls.setmetadata(k, v)

        #log.debug(f"container: converted ({cls.__name__}) to declarative container")
        return newcls
    if cls is None:
        return decorator
    return decorator(cls)
