"""
Transform Decorators
--------------------
Provides decorators for transforming requests and responses.
"""
import typing as t, functools as fn
from clientfactory.log import log

from clientfactory.core.request import Request
from clientfactory.core.response import Response


def preprocess(func=None):
    """
    Decorator to mark a method as a request preprocessor.

    A preprocessor can modify the request before it is sent to the server.
    It should accept a Request object and return a modified Request object.
    """
    def decorator(method):
        if hasattr(method, '_methodconfig'):
            method._methodconfig.preprocess = func
        else:
            method._preprocess = func
        return method
    return decorator


def postprocess(func=None):
    """
    Decorator to mark a method as a response postprocessor.

    A postprocessor can transform the response after it is received from the server.
    It should accept a Response object and return a transformed value.
    """
    def decorator(method):
        if hasattr(method, '_methodconfig'):
            method._methodconfig.postprocess = func
        else:
            method._postprocess = func
        return method
    return decorator


def transformrequest(func: t.Callable[[Request], Request]):
    """Decorator that applies a transformation function to a request."""
    return preprocess(func)


def transformresponse(func: t.Callable[[Response], t.Any]):
    """Decorator that applies a transformation function to a response."""
    return postprocess(func)
