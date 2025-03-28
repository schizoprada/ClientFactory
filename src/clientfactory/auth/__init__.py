# ~/ClientFactory/src/clientfactory/auth/__init__.py
"""
Authentication Management Module
"""
from .base import (
    BaseAuth, AuthError, AuthState, NoAuth
)
from .basic import (
    BasicAuth
)
from .tokens import (
    TokenScheme, TokenError, TokenAuth
)
from .apikey import (
    KeyLocation, APIKeyError, APIKeyAuth
)
from .oauth import (
    OAuthError, OAuthToken, OAuthFlow,
    OAuthConfig, OAuthAuth
)

from .dpop import (
    DpopAuth, DpopError
)

from clientfactory.log import log
#log.remove() # remove logging during initialization

__all__ = [
    'BaseAuth', 'AuthError', 'AuthState',
    'NoAuth', 'BasicAuth', 'TokenError',
    'TokenScheme', 'TokenAuth', 'KeyLocation',
    'APIKeyError', 'APIKeyAuth', 'OAuthError',
    'OAuthToken', 'OAuthFlow', 'OAuthConfig',
    'OAuthAuth', 'DpopAuth', 'DpopError'
]
