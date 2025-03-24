# ~/ClientFactory/src/clientfactory/decorators/resource.py
"""
Resource Decorators
-------------------
Provides decorators for defining API resources in a declarative style.
"""
import inspect, typing as t, functools as fn
from loguru import logger as log

from clientfactory.core.resource import ResourceConfig

def resource(cls=None, path: t.Optional[str] = None, name: t.Optional[str] = None):
    """
    Decorator to define an API resource.

    Marks a class as an API resource and configures its behavior.
    The decorated class will be registered with the client when included
    as a nested class or explicitly registered.
    """
    def wrap(cls):
        if not hasattr(cls, '_resourceconfig'):
            resourcepath = (path or getattr(cls, 'path', cls.__name__.lower()))
            resourcename = (name or cls.__name__)
            log.debug(f"Creating ResourceConfig for {cls.__name__} with path: {resourcepath}")
            cls._resourceconfig = ResourceConfig(
                name=resourcename,
                path=resourcepath,
                methods={},
                children={}
            )
        for mname, method in cls.__dict__.items():
            if mname.startswith('__') or not callable(method):
                continue

            if hasattr(method, '_methodconfig'):
                cls._resourceconfig.methods[mname] = method._methodconfig

        return cls

    if cls is None:
        return wrap
    return wrap(cls)

def subresource(cls=None, path: t.Optional[str] = None, name: t.Optional[str] = None):
    """
    Decorator to define a nested resource.

    Similar to @resource but intended for nested resources.
    """
    return resource(cls, path=path, name=name)
