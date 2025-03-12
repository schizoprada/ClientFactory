from __future__ import annotations
import typing as t
import inspect
from functools import wraps
from clientfactory.utils.request import RequestMethod, Request
from clientfactory.utils.response import Response
from clientfactory.resources.base import ResourceConfig, MethodConfig
from clientfactory.transformers.base import TransformPipeline
from loguru import logger as log


def resource(cls=None, *, path: t.Optional[str] = None):
    """Decorator to define an API resource"""
    def wrap(cls):
        # Create resource config if not exists
        if not hasattr(cls, '_resourcecfg'):
            from clientfactory.resources.base import ResourceConfig
            # check for path in this order:
            # 1. path parameter to decorator
            # 2. path attribbute on class
            # 3. fallback to lowercase class name
            resourcepath = path or getattr(cls, 'path', cls.__name__.lower())
            transforms = getattr(cls, 'transforms', [])
            log.info(f"resource | creating new ResourceConfig with: path[{resourcepath}] :: transforms[{transforms}]")
            cls._resourcecfg = ResourceConfig(
                name=cls.__name__,
                path=resourcepath,
                methods={},
                children={},
                transforms=transforms
            )
            if transforms:
                cls._resourcecfg.pipeline = TransformPipeline(transforms)
            log.info(f"resource | created ResourceConfig: {cls._resourcecfg}")

        # Process all class methods
        log.debug(f"resources.decorators.resource | processing class: {cls.__name__}")
        for name, attr in cls.__dict__.items():
            log.debug(f"resources.decorators.resource | examining attribute: {name}")

            # Handle decorated methods
            if hasattr(attr, '_methodcfg'):
                log.debug(f"resources.decorators.resource | registering decorated method: {name}")
                cls._resourcecfg.methods[name] = attr._methodcfg

            # Handle nested resources
            elif inspect.isclass(attr) and hasattr(attr, '_resourcecfg'):
                log.debug(f"resources.decorators.resource | registering nested resource: {name}")
                childcfg = attr._resourcecfg
                childcfg.parent = cls._resourcecfg
                cls._resourcecfg.children[name] = childcfg

            # Handle undecorated methods
            elif inspect.isfunction(attr) and not name.startswith('_'):
                log.debug(f"resources.decorators.resource | registering undecorated method: {name}")
                from clientfactory.resources.base import MethodConfig
                cls._resourcecfg.methods[name] = MethodConfig(
                    name=name,
                    method=RequestMethod.NA
                )
        return cls

    return wrap if cls is None else wrap(cls)

def decoratormethod(method: RequestMethod):
    """Factory for HTTP method decorators"""
    def decorator(pathorfunc=None):
        def wrap(func):
            cfg = MethodConfig(
                name=func.__name__,
                method=method,
                path=pathorfunc if isinstance(pathorfunc, str) else None
            )

            # Store the original function for later use
            cfg.preprocess = getattr(func, '_preprocess', None)
            cfg.postprocess = getattr(func, '_postprocess', None)

            func._methodcfg = cfg
            return func

        if callable(pathorfunc):
            return wrap(pathorfunc)
        return wrap

    return decorator

# HTTP method decorators
get = decoratormethod(RequestMethod.GET)
post = decoratormethod(RequestMethod.POST)
put = decoratormethod(RequestMethod.PUT)
patch = decoratormethod(RequestMethod.PATCH)
delete = decoratormethod(RequestMethod.DELETE)

def preprocess(func):
    """
    Decorator to mark a method as request preprocessor.
    Can be used as @preprocess or @preprocess(some_method)
    args[func] can be None
    """
    log.debug(f"decorators.preprocess | called with func[{func}]")
    if func is None:
        # Used as @preprocess without args - return the decorator itself
        log.debug(f"decorators.preprocess | called with no args | returning decorator")
        return preprocess
    # If we got a function, we're either:
        # 1. Being used as @preprocess without parentheses
        # 2. Being used as @preprocess(func) with a function argument
    def decorator(method):
        log.debug(f"decorators.preprocess | decorating method[{method.__name__}] with preprocessor[{func.__name__}]")
        @wraps(method)
        def wrapped(*args, **kwargs):
            return method(*args, **kwargs)
        # store the preprocessor - if its an instance method, itll be bound later
        if hasattr(method, '_methodcfg'):
            log.debug(f"decorators.preprocess | storing preprocessor in existing method config")
            method._methodcfg.preprocess = func
        wrapped._preprocess = func
        return wrapped
    #handle direct usage (@preprocess) vs referenced method(@preprocess(method))
    if hasattr(func, '_methodcfg'):
        log.debug(f"decorators.preprocess | storing preprocessor directly on method config for func[{func.__name__}]")
        # Need to store ourselves as the preprocessor, since we're  decorating a method that already has method config
        func._methodcfg.preprocess = func
        return func
    return decorator


def postprocess(func):
    """
    Decorator to mark a method as response postprocessor.
    Can be used as @postprocess or @postprocess(some_method)
    args[func] can be None
    """
    if func is None:
        # Used as @postprocess without args - return the decorator itself
        return postprocess

    # If we got a function, we're either:
    # 1. Being used as @postprocess without parentheses
    # 2. Being used as @postprocess(func) with a function argument
    def decorator(method):
        @wraps(method)
        def wrapped(*args, **kwargs):
            return method(*args, **kwargs)
        # store the postprocessor - if its an instance method, itll be bound later
        if hasattr(method, '_methodcfg'):
            method._methodcfg.postprocess = func
        wrapped._postprocess = func
        return wrapped

    # handle direct usage (@postprocess) vs referenced method(@postprocess(method))
    if hasattr(func, '_methodcfg'):
        # Need to store ourselves as the postprocessor, since we're decorating a method that already has method config
        func._methodcfg.postprocess = func
        return func

    return decorator
