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

from clientfactory.log import log
#log.remove()

__all__ = [
    'DeclarativeMeta', 'DeclarativeComponent', 'DeclarativeContainer',
    'isdeclarative', 'getclassmetadata', 'copymetadata',
    'declarative', 'declarativemethod', 'container'
]
