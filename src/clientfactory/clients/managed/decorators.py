# ~/ClientFactory/src/clientfactory/clients/managed/decorators.py
from __future__ import annotations
import typing as t
from functools import wraps
from clientfactory.resources.decorators import resource
from clientfactory.utils.request import RequestMethod
from clientfactory.resources.base import MethodConfig
from .core import Operation, Operations, OpType, ManagedResourceConfig
from .base import ManagedResource
from loguru import logger as log

def managedop(method: RequestMethod, optype: OpType = OpType.CUSTOM, path: t.Optional[str] = None):
    """
    Decorator for custom managed operations.
    Similar to HTTP method decorators but with managed operation support.
    """
    def decorator(pathorfunc=None):
        def wrap(func):
            operation = Operation(
                type=optype, # more flexible like this
                method=method,
                path=path or (pathorfunc if isinstance(pathorfunc, str) else None)  # Use provided path firste
            )

            # Store operation config
            func._operation = operation

            # Create method config for Resource compatibility
            func._methodcfg = MethodConfig(
                name=func.__name__,
                method=method,
                path=operation.path,
                preprocess=getattr(func, '_preprocess', None),
                postprocess=getattr(func, '_postprocess', None)
            )
            return func

        if callable(pathorfunc):
            return wrap(pathorfunc)
        return wrap

    return decorator

def managedresource(cls=None, *, path: t.Optional[str]=None):
    """
    Decorator to define a managed resource with CRUD operations support.

    Usage:
        @managedresource
        class Resource:
            path = "resource"
            operations = Operations(
                C(RequestMethod.POST),
                R(RequestMethod.GET)
            )
    """
    def wrap(cls):
        # First apply resource decorator
        cls = resource(cls, path=path)

        # Validate required attributes
        if not hasattr(cls, 'operations'):
            cls.operations = Operations()

        # Process any methods decorated with @managedop
        for name, attr in cls.__dict__.items():
            if hasattr(attr, '_operation'):
                log.debug(f"managedresource | found managed operation: {name}")
                cls.operations.add(name, attr._operation)

        # Create managed resource config
        cfg = ManagedResourceConfig(
            name=cls._resourcecfg.name,
            path=cls._resourcecfg.path,
            methods=cls._resourcecfg.methods,
            children=cls._resourcecfg.children,
            parent=cls._resourcecfg.parent,
            operations=cls.operations,
            transforms=getattr(cls, 'transforms', [])
        )

        if cfg.transforms:
            from clientfactory.transformers import TransformPipeline
            cfg.pipeline = TransformPipeline(cfg.transforms)

        cls._resourcecfg = cfg
        cls.__resourceclass__ = ManagedResource

        return cls

    return wrap if cls is None else wrap(cls)
