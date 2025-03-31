# ~/ClientFactory/src/clientfactory/decorators/backend.py
"""
Backend Decorators
-----------------
Provides decorators for defining backend protocols in a declarative style.
"""
from __future__ import annotations
import typing as t, functools as fn
from clientfactory.log import log

from clientfactory.backends.base import Backend, BackendType
from clientfactory.backends.graphql import GraphQL, GQLConfig, GQLVar
from clientfactory.backends.algolia import Algolia, AlgoliaConfig


def backend(cls=None, **kwargs):
    """
    Decorator to define a backend protocol adapter.

    Can be used either directly or with arguments:
        @backend
        class MyBackend:
            ...

        @backend(type=BackendType.CUSTOM)
        class MyBackend:
            ...
    """
    def decorator(cls):
        if not hasattr(cls, '__declarativetype__'):
            cls.__declarativetype__ = 'backend'

        for k, v in kwargs.items():
            if hasattr(cls, k):
                setattr(cls, k, v)

            if hasattr(cls, 'setmetadata'):
                cls.setmetadata(k, v)

        return cls

    if cls is None:
        return decorator
    return decorator(cls)

def graphql(cls=None, *, operation: t.Optional[str] = None, query: t.Optional[str] = None, variables: t.Optional[dict] = None):
    """
    Decorator for GraphQL backend.

    Example:
        @graphql(operation="MyQuery", query="{ ... }", variables={...})
        class MyGraphQL:
            ...
    """
    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, GraphQL):
            if operation is not None:
                cls.config.operation = operation
            if query is not None:
                cls.config.query = query
            if variables is not None:
                cls.config.variables = variables
            return cls

        config = GQLConfig(
            operation = (operation or getattr(cls, 'operation', '')),
            query = (query or getattr(cls, 'query', '')),
            variables = (variables or getattr(cls, 'variables', {}))
        )
        return GraphQL(config=config)

    if cls is None:
        return decorator
    return decorator(cls)

def algolia(cls=None, *, appid: t.Optional[str] = None, apikey: t.Optional[str] = None, indices: t.Optional[list[str]] = None):
    """
    Decorator for Algolia backend.

    Example:
        @algolia(appid="APPID", apikey="APIKEY", indices=["index1", "index2"])
        class MyAlgolia:
            ...
    """
    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, Algolia):
            if appid is not None:
                cls.config.appid = appid
            if apikey is not None:
                cls.config.apikey = apikey
            if indices is not None:
                cls.config.indices = indices
            return cls

        # Extract config from class attributes if not provided
        config = AlgoliaConfig(
            appid=(appid or getattr(cls, 'appid', '')),
            apikey=(apikey or getattr(cls, 'apikey', '')),
            indices=(indices or getattr(cls, 'indices', []))
        )
        return Algolia(config=config)

    if cls is None:
        return decorator
    return decorator(cls)
