# ~/ClientFactory/src/clientfactory/declarative/resource.py
"""
Declarative Resources
---------------------
Resource-specific declarative components.
Provides classes and decorators for defining API resources in a declarative style.
"""
from __future__ import annotations
import typing as t
from loguru import logger as log

from clientfactory.declarative.base import DeclarativeContainer
from clientfactory.declarative.decorators import declarative, declarativemethod, container

class DeclarativeResource(DeclarativeContainer):
    """
    Base class for declarative API resources.

    Enhances DeclarativeContainer with resource-specific functionality for defining API endpoints and path handling.
    """

    __declarativetype__ = 'resource'

    path: str = ""
    name: t.Optional[str] = None

    @classmethod
    def _processclassattributes(cls) -> None:
        """Process resource-specific class attributes."""
        log.debug(f"DeclarativeResource: starting attribute processing for ({cls.__name__})")
        log.debug(f"DeclarativeResource: current metadata before processing: {cls.__metadata__}")

        # Set name FIRST, before any inheritance
        if ('name' not in cls.__metadata__):
            cls.__metadata__['name'] = cls.__name__.lower()
            log.debug(f"DeclarativeResource: set name to ({cls.__metadata__['name']}) for: {cls.__name__}")
        else:
            log.debug(f"DeclarativeResource: name already set to ({cls.__metadata__['name']}) for: {cls.__name__}")

        # Then do normal processing
        log.debug(f"DeclarativeResource: calling super()._processclassattributes for: {cls.__name__}")
        super()._processclassattributes()
        log.debug(f"DeclarativeResource: returned from super()._processclassattributes for: {cls.__name__}")
        log.debug(f"DeclarativeResource: metadata after super(): {cls.__metadata__}")

        # Process path after other attributes
        if ('path' not in cls.__metadata__) and (hasattr(cls, 'path')):
            cls.__metadata__['path'] = cls.path.lstrip('/').rstrip('/')
            log.debug(f"DeclarativeResource: extracted path ({cls.path}) from: {cls.__name__}")

        log.debug(f"DeclarativeResource: completed processing for ({cls.__name__}) - final metadata: {cls.__metadata__}")


    @classmethod
    def getfullpath(cls) -> str:
        """
        Get the full path of the resource including parent paths.

        Traverses the parent to chain to build the complete resource path.
        """
        pathparts = []
        current = cls
        seen = set()

        while current and id(current) not in seen:
            seen.add(id(current))
            if hasattr(current, '__metadata__') and ('path' in current.__metadata__):
                if (mpath:=current.__metadata__.get('path', '')):
                    pathparts.append(mpath.lstrip('/').rstrip('/'))
                current = current.__metadata__.get('parent')
            else:
                break


        pathparts.reverse()

        return '/' + '/'.join(pathparts)


    @classmethod
    def getmethods(cls) -> dict:
        """Get all declarative methods defined on this resource."""
        return cls.__metadata__.get('methods', {})

    @classmethod
    def getnestedresources(cls) -> dict:
        """Get all nested resources defined on this resource."""
        return cls.__metadata__.get('components', {})


def resource(cls=None, *, path: t.Optional[str] = None, name: t.Optional[str] = None):
    """
    Decorator to define an API resource.

    Ensures that a class is a subclass of DeclarativeResource and sets resource-specific metadata.
    """
    metadata = {}
    attributes = {
        'path': path,
        'name': name
    }
    for k, v in attributes.items():
        if v is not None:
            metadata[k] = v

    def decorator(cls):
        parent = (
            cls.__module__.split('.')[-1]
            if '.' in cls.__module__
            else None
        )
        if isinstance(cls, type) and issubclass(cls, DeclarativeResource):
            for k, v in metadata.items():
                cls.setmetadata(k, v)

            if path is not None:
                cls.path = path.lstrip('/').rstrip('/')

            return cls

        if issubclass(cls, DeclarativeContainer):
            bases = tuple(b if b!=DeclarativeContainer else DeclarativeResource for b in cls.__bases__)
        else:
            bases = (DeclarativeResource,) + cls.__bases__

        newcls = type(cls.__name__, bases, dict(cls.__dict__))

        for key, val in metadata.items():
            newcls.setmetadata(key, val)

            for k, v in attributes.items():
                if v is not None:
                    setattr(newcls, k, v)

        log.debug(f"resource: converted ({cls.__name__}) to declarative resource")
        return newcls

    if cls is None:
        return decorator
    return decorator(cls)
