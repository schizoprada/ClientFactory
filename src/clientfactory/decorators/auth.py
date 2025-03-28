# ~/ClientFactory/src/clientfactory/decorators/auth.py
"""
Auth Decorators
-------------------
Provides decorators for defining auth providers in a declarative style.
"""
from __future__ import annotations
import typing as t, functools as fn
from clientfactory.log import log

from clientfactory.declarative import DeclarativeContainer
from clientfactory.auth import (
    AuthError, BaseAuth, BasicAuth,
    APIKeyAuth, TokenAuth, OAuthAuth,
    DpopAuth
)

authoptions = (BaseAuth, BasicAuth, APIKeyAuth, OAuthAuth, TokenAuth)

def authprovider(cls=None, **kwargs):
    """
    Decorator to define an auth provider.

    Can be used either directly or with arguments:
        @authprovider # will default to base type of BaseAuth
        class MyAuth:
            ...

        @authprovider(name="custom", authtype=TokenAuth)
        class MyAuth:
            ...
    """
    authtype = kwargs.get('authtype', BaseAuth)
    validtype = (
        isinstance(authtype, type)
        and
        (
            authtype in authoptions
            or
            any(
                issubclass(authtype, t)
                for t in authoptions
            )
        )
    )
    if not validtype:
        raise AuthError(
                    f"Invalid authtype ({authtype.__name__ if isinstance(authtype, type) else authtype})"
                    f" - must be one of: {[t.__name__ for t in authoptions]}"
                )

    metadata = kwargs

    def decorator(cls):
        if isinstance(cls, type) and issubclass(cls, authoptions):
            for k, v in metadata.items():
                cls.setmetadata(k, v)
            return cls

        bases = (authtype, ) + cls.__bases__
        newcls = type(cls.__name__, bases, dict(cls.__dict__))

        for k, v in metadata.items():
            newcls.setmetadata(k, v)

        log.debug(f"authprovider: created auth provider ({newcls.__name__})")
        return newcls

    if cls is None:
        return decorator
    return decorator(cls)


def specificprovider(cls=None, authtype=BaseAuth, **kwargs):
    if cls is None:
        return lambda c: authprovider(c, authtype=authtype, **kwargs)
    return authprovider(cls, authtype=authtype, **kwargs)

class auth:
    """Collection of specific auth provider decorators"""
    basic = staticmethod(fn.partial(specificprovider, authtype=BaseAuth))
    apikey = staticmethod(fn.partial(specificprovider, authtype=APIKeyAuth))
    token = staticmethod(fn.partial(specificprovider, authtype=TokenAuth))
    oauth = staticmethod(fn.partial(specificprovider, authtype=OAuthAuth))
    dpop = staticmethod(fn.partial(specificprovider, authtype=DpopAuth))
