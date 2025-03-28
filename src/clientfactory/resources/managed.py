# ~/ClientFactory/src/clientfactory/resources/managed.py
"""
Managed Resource
----------------
Resource implementation for CRUD operations with standardized methods.
"""
from __future__ import annotations
import enum, typing as t
from dataclasses import dataclass, field
from clientfactory.log import log

from clientfactory.core.resource import ResourceConfig, MethodConfig
from clientfactory.core.request import RequestMethod, RM, Request
from clientfactory.core.response import Response
from clientfactory.core.payload import Payload
from clientfactory.core.session import Session
from clientfactory.resources.base import SpecializedResource


class OperationType(enum.Enum):
    """Types of standard CRUD operations"""
    CREATE = enum.auto()
    READ = enum.auto()
    UPDATE = enum.auto()
    DELETE = enum.auto()
    LIST = enum.auto()
    CUSTOM = enum.auto()

@dataclass
class Operation:
    """Definition of a standard operation"""
    type: OperationType
    method: RequestMethod
    path: t.Optional[str] = None
    payload: t.Optional[Payload] = None
    preprocess: t.Optional[t.Callable[[Request], Request]] = None
    postprocess: t.Optional[t.Callable[[Response], t.Any]] = None

@dataclass
class ManagedResourceConfig(ResourceConfig):
    """Configuration for managed resources with CRUD operations"""
    operations: t.Dict[str, Operation] = field(default_factory=dict)


class ManagedResource(SpecializedResource):
    """
    Resource implementation with standardized CRUD operations.

    Provides a consistent interface for creating, reading, updating, and deleting
    resources with standard naming and behavior.
    """

    __declarativetype__ = 'managed'
    operations: t.Dict[str, Operation] = {}

    def __init__(self, session: Session, config: ManagedResourceConfig):
        super().__init__(session, config)
        self._operations = (config.operations or {})

    def _processattributes(self, config: ResourceConfig):
        if not isinstance(config, ManagedResourceConfig):
            managedconfig = ManagedResourceConfig(
                name=config.name,
                path=config.path,
                methods=config.methods.copy(),
                children=config.children.copy(),
                parent=config.parent
            )
            config.__class__ = ManagedResourceConfig
            for k, v in managedconfig.__dict__.items():
                setattr(config, k, v)
        for k, v in self._attributes:
            if hasattr(config, k):
                setattr(config, k, v)

    def _setupspecialized(self):
        """Set up CRUD operations."""
        operations = self.getmetadata('operations', {})
        for name, operation in operations.items():
            if not hasattr(self, name):
                log.debug(f"Registering operation: {name}")

                methodconfig = MethodConfig(
                    name=name,
                    method=operation.method,
                    path=operation.path,
                    preprocess=operation.preprocess,
                    postprocess=operation.postprocess,
                    payload=operation.payload
                )

                self._config.methods[name] = methodconfig
                setattr(self, name, self._createmethod(methodconfig))



    def withoperations(self, config: ResourceConfig, operations: t.Dict[str, Operation]) -> ManagedResource:
        """Create a managed resource from a standard resource configuration."""
        config = ManagedResourceConfig(
            name=config.name,
            path=config.path,
            methods=config.methods.copy(),
            children=config.children.copy(),
            parent=config.parent,
            operations=operations
        )
        return self.__class__(self._session, config)


# common operations shorthand
## should make decorators to match too tbh
def createop(path: str = "", payload: t.Optional[Payload] = None, **kwargs) -> Operation:
    """Create a CREATE operation"""
    data = {
        'type': OperationType.CREATE,
        'method': RM.POST,
        'path': path,
        'payload': payload
    }
    data.update(kwargs)
    return Operation(**data)

def readop(path: str = "{id}", **kwargs) -> Operation:
    """Create a READ operation"""
    data = {
        'type': OperationType.READ,
        'method': RM.GET,
        'path': path
    }
    data.update(kwargs)
    return Operation(**data)

def updateop(path: str = "{id}", payload: t.Optional[Payload] = None, **kwargs) -> Operation:
    data = {
        'type': OperationType.UPDATE,
        'method': RM.PUT,
        'path': path,
        'payload': payload
    }
    data.update(kwargs)
    return Operation(**data)

def deleteop(path: str = "{id}", **kwargs) -> Operation:
    data = {
        'type': OperationType.DELETE,
        'method': RM.DELETE,
        'path': path,
    }
    data.update(kwargs)
    return Operation(**data)

def listop(path: str = "", **kwargs) -> Operation:
    data = {
        'type': OperationType.LIST,
        'method': RM.GET,
        'path': path
    }
    data.update(kwargs)
    return Operation(**data)
