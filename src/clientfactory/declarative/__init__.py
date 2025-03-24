# ~/ClientFactory/src/clientfactory/declarative/__init__.py
"""
Declarative Module
------------------
"""

from .base import (
    DeclarativeMeta, DeclarativeComponent, DeclarativeContainer,
    isdeclarative, getclassmetadata, copymetadata
)

from .decorators import (
    declarative, declarativemethod, container
)

from .resource import (
    DeclarativeResource, resource
)

from .client import (
    DeclarativeClient, client
)

__all__ = [
    'DeclarativeMeta', 'DeclarativeComponent', 'DeclarativeContainer',
    'DeclarativeResource', 'DeclarativeClient', 'isdeclarative',
    'getclassmetadata', 'copymetadata', 'declarative',
    'declarativemethod', 'container', 'resource',
    'client'
]
