# ~/ClientFactory/src/clientfactory/clients/managed/core.py
from __future__ import annotations
import enum, typing as t
from dataclasses import dataclass, field
from clientfactory.resources.base import ResourceConfig
from clientfactory.resources.decorators import postprocess
from clientfactory.utils.request import RequestMethod
from clientfactory.transformers.base import Transform
from loguru import logger as log

class OpType(enum.Enum):
    CREATE = enum.auto()
    READ = enum.auto()
    UPDATE = enum.auto()
    DELETE = enum.auto()
    CUSTOM = enum.auto()

@dataclass
class Operation:
    type: OpType
    method: RequestMethod
    path: t.Optional[str] = None
    transforms: t.List[Transform] = field(default_factory=list)
    preprocess: t.Optional[t.Callable] = None
    postprocess: t.Optional[t.Callable] = None
    validators: t.List[t.Callable] = field(default_factory=list)

    def __post_init__(self):
        log.debug(f"Operation.__post_init__ | initializing operation[{self.type}] method[{self.method}]")

# Convenience classes for CRUD operations
class C(Operation):
    """Create operation shorthand"""
    def __init__(self, method: RequestMethod = RequestMethod.POST, **kwargs):
        super().__init__(type=OpType.CREATE, method=method, **kwargs)

class R(Operation):
    """Read operation shorthand"""
    def __init__(self, method: RequestMethod = RequestMethod.GET, **kwargs):
        super().__init__(type=OpType.READ, method=method, **kwargs)

class U(Operation):
    """Update operation shorthand"""
    def __init__(self, method: RequestMethod = RequestMethod.PUT, **kwargs):
        super().__init__(type=OpType.UPDATE, method=method, **kwargs)

class D(Operation):
    """Delete operation shorthand"""
    def __init__(self, method: RequestMethod = RequestMethod.DELETE, **kwargs):
        super().__init__(type=OpType.DELETE, method=method, **kwargs)

@dataclass
class Operations:
    """Collection of resource operations"""
    operations: t.Dict[str, Operation] = field(default_factory=dict)

    def __init__(self, *ops: Operation):
        self.operations  = {}
        for op in ops:
            name = op.type.name.lower()
            self.operations[name] = op
            log.debug(f"Operations.__init__ | registered operation[{name}]")

    def get(self, name: str) -> t.Optional[Operation]:
        """Get operation by name"""
        return self.operations.get(name)

    def add(self, name: str, operation: Operation):
        """Add or update an operation"""
        self.operations[name] = operation
        log.debug(f"Operations.add | added operation[{name}]")
        return self # for chaining e.g. operation.add(w, x).add(y, z)

    def remove(self, name: str):
        """Remove an operation"""
        if name in self.operations:
            del self.operations[name]
            log.debug(f"Operations.remove | removed operation[{name}]")
        return self

@dataclass
class ManagedResourceConfig(ResourceConfig):
    """Configuration for managed resources"""
    operations: Operations = field(default_factory=Operations)
