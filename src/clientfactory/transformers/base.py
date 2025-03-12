# ~/ClientFactory/src/clientfactory/transformers/base.py
import enum, typing as t, functools as fn
from abc import ABC, abstractmethod
from dataclasses import dataclass
from loguru import logger as log

class TransformType(enum.Enum):
    URL = "url"
    PAYLOAD = "payload"
    PARAMS = "params"
    HEADERS = "headers"
    COOKIES = "cookies"
    CUSTOM = "custom"

class TransformOperation(enum.Enum):
    MERGE = "merge"
    MAP = "map"
    FILTER = "filter"
    CHAIN = "chain"
    COMPOSE = "compose"
    CUSTOM = "custom"


class MergeMode(enum.Enum):
    UPDATE = "update"
    NESTEDONLY = "nestedonly"
    ROOTONLY = "rootonly"
    # add more merge modes

class DEFAULT:
    @staticmethod
    def CONTEXT() -> dict:
        return {
        'processed': set(),
        'history': []
    }

class Transform(ABC):
    """Abstract base for all transforms"""
    def __init__(self, type:TransformType, operation:TransformOperation, target:t.Optional[str] = None, order:int = 0, context:dict = {}):
        self.type = type
        self.operation = operation
        self.target = target
        self.order = order
        self.context = context

    @abstractmethod
    def apply(self, value: t.Any, context: t.Optional[dict] = None) -> t.Any:
        """Apply transformation"""
        self.context = (context or self.context)
        pass

    def compose(self, other: 'Transform') -> 'Transform':
        """Compose with another transform"""
        return ComposedTransform(self, other)

    def __rshift__(self, other: 'Transform') -> 'Transform':
        """Override `>>` operator for composition"""
        return self.compose(other)

    def __call__(self, value:t.Any) -> t.Any:
        """Callable transforms application"""
        return self.apply(value)

class ComposedTransform(Transform):
    """Represents composition of multiple transforms"""
    def __init__(self, first: Transform, second: Transform):
        super().__init__(
            type=first.type,
            operation=TransformOperation.COMPOSE,
            order=max(first.order, second.order)
        )
        self.first = first
        self.second = second

    def apply(self, value: t.Any) -> t.Any:
        return self.second.apply(self.first.apply(value))


class TransformPipeline:
    """Manage sequence of transformations with enhanced composition"""
    def __init__(self, transforms:t.List[(Transform | None)] = []):
        self.transforms = transforms

    def add(self, transform: Transform) -> 'TransformPipeline':
        self.transforms.append(transform)
        return self

    def compose(self, other: 'TransformPipeline') -> 'TransformPipeline':
        """Compose with another pipeline"""
        return TransformPipeline(self.transforms + other.transforms)

    def execute(self, value: t.Any) -> t.Any:
        """Execute transform pipeline"""
        log.debug(f"TransformPipeline.execute | starting with value: {value}")
        sortedtransforms = sorted(self.transforms, key=lambda t: t.order)
        log.debug(f"TransformPipeline.execute | transform order: {[t.__class__.__name__ for t in sortedtransforms]}")

        context = DEFAULT.CONTEXT()

        result = fn.reduce(
            lambda acc, transform: transform.apply(acc, context),
            sortedtransforms,
            value
        )
        log.debug(f"TransformPipeline.execute | final result: {result}")
        return result

    def __call__(self, value: t.Any) -> t.Any:
        return self.execute(value)


class Transformer:
    """Factory class for creating and managing transforms"""
    def __init__(self, transforms: t.Optional[t.List[Transform]] = None):
        self.pipelines: t.Dict[str, TransformPipeline] = {}
        if transforms:
            self.pipelines["default"] = TransformPipeline(transforms)

    def pipeline(self, name:str) -> TransformPipeline:
        if name not in self.pipelines:
            self.pipelines[name] = TransformPipeline()
        return self.pipelines[name]

    def execute(self, name:str, value: t.Any) -> t.Any:
        if value is None: value = {}
        return self.pipeline(name)(value)

    def __call__(self, *args, **kwargs) -> t.Any:
        return self.execute(*args, **kwargs)
