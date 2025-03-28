# ~/ClientFactory/src/clientfactory/decorators/method.py
"""
Method Decorators
-----------------
Provides decorators for definign API methods in a declarative style.
"""
import typing as t, functools as fn
from clientfactory.log import log

from clientfactory.core.resource import MethodConfig
from clientfactory.core.request import RequestMethod, RM
from clientfactory.core.payload import Payload

def httpmethod(methodtype: RequestMethod, path: t.Optional[str] = None, **kwargs):
    """Base decorator for HTTP methods."""

    def decorator(func):
        func._methodconfig = MethodConfig(
            name=func.__name__,
            method=methodtype,
            path=path,
            preprocess=kwargs.get('preprocess'),
            postprocess=kwargs.get('postprocess'),
            payload=kwargs.get('payload'),
            description=kwargs.get('description', (func.__doc__ or ""))
        )
        return func
    return decorator


def methodwithpayload(httpfunc, payload: Payload, **kwargs):
    """Helper to create a method decorator with a payload."""
    return fn.partial(httpfunc, payload=payload, **kwargs)


methodtypes = {RM.GET, RM.POST, RM.PUT, RM.PATCH, RM.DELETE, RM.HEAD, RM.OPTIONS}
get, post, put, patch, delete, head, options = (fn.partial(httpmethod, methodtype) for methodtype in methodtypes)


get.__doc__ = (
"""
Decorator for GET requests.

Args:
    path: Endpoint path (can include parameters like {id})
    **kwargs: Additional configuration options

Example:
    @get("users/{id}")
    def get_user(self, id): pass
"""
)

post.__doc__ = (
"""
Decorator for POST requests.

Args:
    path: Endpoint path
    **kwargs: Additional configuration options

Example:
    @post("users")
    def create_user(self, **data): pass
"""
)

put.__doc__ = (
"""
Decorator for PUT requests.

Args:
    path: Endpoint path
    **kwargs: Additional configuration options

Example:
    @put("users/{id}")
    def update_user(self, id, **data): pass
"""
)

patch.__doc__ = (
"""
Decorator for PATCH requests.

Args:
    path: Endpoint path
    **kwargs: Additional configuration options

Example:
    @patch("users/{id}")
    def partial_update(self, id, **data): pass
"""
)

delete.__doc__ = (
"""
Decorator for DELETE requests.

Args:
    path: Endpoint path
    **kwargs: Additional configuration options

Example:
    @delete("users/{id}")
    def delete_user(self, id): pass
"""
)

head.__doc__ = (
"""
Decorator for HEAD requests.

Args:
    path: Endpoint path
    **kwargs: Additional configuration options

Example:
    @head("users/{id}")
    def check_user(self, id): pass
"""
)

options.__doc__ = (
"""
Decorator for OPTIONS requests.

Args:
    path: Endpoint path
    **kwargs: Additional configuration options

Example:
    @options("users")
    def get_options(self): pass
"""
)
