# ~/ClientFactory/src/clientfactory/decorators/resource.py
"""
Resource Decorators
-------------------
Provides decorators for defining API resources in a declarative style.
"""
import inspect, typing as t, functools as fn
from clientfactory.log import log

from clientfactory.core.resource import ResourceConfig, Resource
from clientfactory.declarative import DeclarativeContainer

def resource(
    cls=None,
    *,
    path: t.Optional[str] = None,
    name: t.Optional[str] = None,
    variant: t.Optional[t.Type[Resource]] = None # changed to not conflict with `type` keyword
):
    """
    Decorator to define an API resource.

    Marks a class as an API resource and configures its behavior.
    The decorated class will be registered with the client when included
    as a nested class or explicitly registered.
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
        classtype = (variant or Resource)

        # type checking
        cls._resourcetype = classtype
        if isinstance(cls, type) and issubclass(cls, classtype):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
                if k == 'path':
                    cls.path = v.lstrip('/').rstrip('/')
            return cls

        if issubclass(cls, DeclarativeContainer):
            bases = tuple(b if b!=DeclarativeContainer else classtype for b in cls.__bases__)
        else:
            bases = (classtype,) + cls.__bases__

        newcls = type(cls.__name__, bases, dict(cls.__dict__))

        for k, v in metadata.items():
            newcls.setmetadata(k, v)
            if v is not None:
                setattr(newcls, k, v)

        resourcepath = (path or getattr(newcls, 'path', newcls.__name__.lower()))
        resourcename = (name or newcls.__name__)

        newcls._resourceconfig = ResourceConfig(
            name=resourcename,
            path=resourcepath.lstrip('/').rstrip('/'),
            methods={},
            children={}
        )

        for mname, method in newcls.__dict__.items():
            if (mname.startswith('__')) or (not callable(method)):
                continue
            if hasattr(method, '_methodconfig'):
                newcls._resourceconfig.methods[mname] = method._methodconfig

        newcls._resourcetype = (variant or Resource)

        log.debug(f"resource: created resource ({newcls.__name__}) with path: {resourcepath}")
        return newcls

    if cls is None:
        return decorator
    return decorator(cls)


def searchresource(cls=None, config: t.Optional[t.Union[ResourceConfig, t.Type[ResourceConfig]]] = None, **kwargs):
    """Decorator for search resources"""
    from clientfactory.resources.search import SearchResource
    from clientfactory.utils.internal import attributes

    def decorator(cls):
        collectedattrs = attributes.collect(cls, ['payload', 'requestmethod', 'path', 'name', 'backend'], includemetadata=True, includeconfig=True)
        for k, v in kwargs.items():
            if k not in collectedattrs:
                collectedattrs[k] = v
        decorated = resource(cls, variant=SearchResource, **kwargs)
        decorated._attributes = collectedattrs
        return decorated

    if cls is None:
        return decorator
    return decorator(cls)


def managedresource(cls=None, **kwargs):
    from clientfactory.resources.managed import ManagedResource
    if cls is None:
        return lambda c: resource(c, variant=ManagedResource, **kwargs)
    return resource(cls, variant=ManagedResource, **kwargs)
