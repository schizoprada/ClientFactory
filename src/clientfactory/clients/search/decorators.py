# ~/ClientFactory/src/clientfactory/clients/search/decorators.py
from __future__ import annotations
import typing as t, functools as fn
from clientfactory.clients.search.base import SearchResource
from clientfactory.clients.search.core import SearchResourceConfig
from clientfactory.utils import Request, Response, RequestMethod
from clientfactory.resources.decorators import resource
from clientfactory.clients.search.core import Protocol, Payload, ProtocolType
from clientfactory.clients.search.adapters import Adapter
from loguru import logger as log

P = t.ParamSpec('P') # wtf is paramspec and typevar tbh
T = t.TypeVar('T')

def searchmethod(func: t.Callable[P, T]) -> t.Callable[P, T]:
    """Marks a method as a search method and handles parameter mapping/validation"""
    @fn.wraps(func)
    def wrapper(self, *args, **kwargs):
        params = kwargs
        if hasattr(self, 'payload'):
            if not self.payload.validate(**kwargs):
                return None # maybe allow for custom invalid handling
            params = self.payload.map(**kwargs)
        return func(*args, **params)
    setattr(wrapper, '_searchmethod', True)
    return wrapper

def searchresource(cls=None, *, path: t.Optional[str]=None):
    """Decorator to define a search resource with protocol/adapter support"""
    def wrap(cls):
        # ensure path is not None
        resourcepath = path or getattr(cls, 'path', cls.__name__.lower())
        log.info(f"searchdecorator | initial resource path: {resourcepath}")

        # First apply resource decorator
        cls = resource(cls, path=resourcepath)
        log.info(f"searchdecorator | after resource decorator, cls._resourcecfg.path: {cls._resourcecfg.path}")
        log.info(f"searchdecorator | after resource decorator, cls._resourcecfg.parent: {cls._resourcecfg.parent}")

        # Validate required attributes
        if not hasattr(cls, 'protocol'):
            raise ValueError(f"Search resource {cls.__name__} requires protocol")

        # draw from cls._resoucecfg now that it has it after `resource(cls)`
        cfg = SearchResourceConfig(
            name=cls._resourcecfg.name,
            path=cls._resourcecfg.path,
            methods=cls._resourcecfg.methods,
            children=cls._resourcecfg.children,
            parent=cls._resourcecfg.parent,
            protocol=cls.protocol,
            payload=getattr(cls, 'payload', Payload()),
            oncall=getattr(cls, 'oncall', False),
            adaptercfg=getattr(cls, 'adaptercfg', None),
            transforms=getattr(cls, 'transforms', [])
        )
        log.info(f"searchdecorator | created SearchResourceConfig with path: {cfg.path}")
        log.info(f"searchdecorator | created SearchResourceConfig with parent: {cfg.parent}")

        if cfg.transforms:
            from clientfactory.transformers import TransformPipeline
            cfg.pipeline = TransformPipeline(cfg.transforms)

        # Add execute method to resource config
        from clientfactory.resources.base import MethodConfig
        cfg.methods['execute'] = MethodConfig(
            name='execute',
            method=cls.protocol.method
        )

        cls._resourcecfg = cfg
        cls.__resourceclass__ = SearchResource

        log.info(f"searchdecorator | final cls._resourcecfg.path: {cls._resourcecfg.path}")
        log.info(f"searchdecorator | final cls._resourcecfg.parent: {cls._resourcecfg.parent}")

        return cls
    return wrap if cls is None else wrap(cls)
