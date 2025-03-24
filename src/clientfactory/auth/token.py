# ~/ClientFactory/src/clientfactory/auth/token.py
"""
Token Authentication Module
---------------------------
Implements token-based authentication (including Bearer tokens).
"""
from __future__ import annotations
from re import L
import enum, typing as t
from datetime import datetime, timedelta

from clientfactory.core import Request
from clientfactory.auth.base import BaseAuth, AuthError, AuthState

class TokenScheme(str, enum.Enum):
    """Standard HTTP Authentication Schemes"""
    BEARER = "Bearer"
    TOKEN = "Token"
    JWT = "JWT"
    MAC = "MAC"
    HAWK = "Hawk"
    CUSTOM = "Custom"

class TokenError(AuthError):
    """Raised for token-related exceptions."""
    pass

class TokenAuth(BaseAuth):
    """
    Token Authentication provider.

    Supports various token schemes inclusing Bearer tokens.
    Adds the token to the Authorization header.
    """

    def __init__(
        self,
        token: str,
        scheme: (str | TokenScheme) = TokenScheme.BEARER,  # consider mapping to an Enum
        expiresin: t.Optional[int] = None
    ):
        """Initialize with token."""
        super().__init__()
        self.token = token
        self.scheme = self._setscheme(scheme)

        self.state.token = token
        self.state.authenticated = bool(token)

        if expiresin is not None:
            self.state.expires = (datetime.now() + timedelta(seconds=expiresin))


    def _setscheme(self, scheme:  (str | TokenScheme)) -> TokenScheme:
        """Safely set the scheme value"""
        if isinstance(scheme, str) and not isinstance(scheme, TokenScheme):
            try:
                return TokenScheme(scheme)
            except ValueError as e:
                raise TokenError(f"Failed to set token scheme: {e}")
        else:
            return scheme


    def _authenticate(self) -> bool:
        """
        Validate token existence.

        For token auth, we just check that a token is provided
        """
        if not self.token:
            raise TokenError("Token is required")
        return True

    def _prepare(self, request: Request) -> Request:
        """
        Add token to the request.
        """
        headers = dict(request.headers or  {})

        if self.scheme:
            headers['Authorization'] = f"{self.scheme.value} {self.token}"
        else:
            headers['Authorization'] = self.token

        return request.clone(headers=headers)

    def updatetoken(self, token: str, expiresin: t.Optional[int] = None) -> None:
        """
        Update the token.
        """
        self.token = token
        self.state.token = token
        self.state.authenticated = True

        if expiresin is not None:
            self.state.expires = (datetime.now() + timedelta(seconds=expiresin))
        else:
            self.state.expires = None

    @classmethod
    def Bearer(cls, token: str, expiresin: t.Optional[int] = None) -> TokenAuth:
        """
        Create a Bearer token authentication provider.
        """
        return cls(token, TokenScheme.BEARER, expiresin)

    @classmethod
    def Token(cls, token: str, expiresin: t.Optional[int] = None) -> TokenAuth:
        """
        Create a Token token authentication provider.
        """
        return cls(token, TokenScheme.TOKEN, expiresin)

    @classmethod
    def JWT(cls, token: str, expiresin: t.Optional[int] = None) -> TokenAuth:
        """
        Create a JWT token authentication provider.
        """
        return cls(token, TokenScheme.JWT, expiresin)

    @classmethod
    def MAC(cls, token: str, expiresin: t.Optional[int] = None) -> TokenAuth:
        """
        Create a MAC token authentication provider.
        """
        return cls(token, TokenScheme.MAC, expiresin)

    @classmethod
    def Hawk(cls, token: str, expiresin: t.Optional[int] = None) -> TokenAuth:
        """
        Create a Hawk token authentication provider.
        """
        return cls(token, TokenScheme.HAWK, expiresin)

    @classmethod
    def Custom(cls, token: str, expiresin: t.Optional[int] = None) -> TokenAuth:
        """
        Create a Custom token authentication provider.
        """
        return cls(token, TokenScheme.CUSTOM, expiresin)
