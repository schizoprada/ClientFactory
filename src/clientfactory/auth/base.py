# ~/ClientFactory/src/clientfactory/auth/base.py
"""
Authentication Base Module
--------------------------
Defines base classes and interfaces for authentication providers
"""
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field
from datetime import datetime

from clientfactory.core import Request
from clientfactory.declarative import DeclarativeComponent


class AuthError(Exception):
    """Raised for authentication related exceptions"""
    pass

@dataclass
class AuthState:
    """Represents the current state of an authentication session"""
    authenticated: bool = False
    token: t.Optional[str] = None
    expires: t.Optional[datetime] = None
    metadata: dict[str, t.Any] = field(default_factory=dict)

    @property
    def expired(self) -> bool:
        """Check if the authentication has expired"""
        if self.expires is None:
            return False
        return (datetime.now() > self.expires)

class BaseAuth(DeclarativeComponent):
    """
    Base class for authentication providers.

    Handles authentication state management and provides methods
    for authenticating and preparing requests with authentication credentials.

    Authentication providers should inherit from this class and implement
    the `_authenticate` and `_prepare` methods
    """

    __declarativetype__ = 'auth'

    def __init__(self, **kwargs):
        """Initialize auth provider with default state"""
        self.state = AuthState()

        # initialize from metadata
        for k, v in self.getallmetadata().items():
            if (not k.startswith('_')) and (hasattr(self, k)):
                setattr(self, k, v)

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @classmethod
    def _processclassattributes(cls) -> None:
        """Process auth-specific class attributes into metadata"""
        super()._processclassattributes()
        for name, value in vars(cls).items():
            if (
                not name.startswith('_')
                and not callable(value)
                and not isinstance(value, type)
                and not isinstance(value, property)
            ):
                cls.__metadata__[name] = value

    def _authenticate(self) -> bool:
        """
        Perform provider-specific authentication.

        Subclasses must implement this method to perform their specific authentication logic.
        """
        return True # default implementation for providers that dont need auth

    def _prepare(self, request: Request) -> Request:
        """
        Add provider-specific authentication to a request.

        Subclasses must implement this method to add thier credentials to the request.
        """
        return request # default implementation just returns the request provided

    def authenticate(self) -> bool:
        """
        Perform authentication and update state.
        """
        try:
            if self._authenticate():
                self.state.authenticated = True
                return True
            return False
        except Exception as e:
            self.state.authenticated = False
            raise

    def prepare(self, request: Request) -> Request:
        """
        Add authentication credentials to a request.

        If not authenticated, will attempt to authenticate first.
        """
        if (not self.state.authenticated) and (not self.authenticate()):
            raise AuthError(f"Not authenticated")

        if (self.state.expired) and (not self.authenticate()):
            raise AuthError(f"Authentication expired and refresh failed")

        return self._prepare(request)

    def refresh(self) -> bool:
        """
        Refresh authentication credentials if possible.

        The default implementation simply re-authenticates.
        Subclasses may override this to implement more efficient token refresh.
        """
        return self.authenticate()

    def clear(self) -> None:
        """Reset the authentication state"""
        self.state = AuthState()

    @property
    def isauthenticated(self) -> bool:
        """Check if currently authenticated and not expired"""
        return self.state.authenticated and not self.state.expired


class NoAuth(BaseAuth):
    """
    Authentication provider that does not perform any authentication.

    Useful for APIs that dont require authentication or for testing.
    """

    def __init__(self):
        """Initialize with authenticated state"""
        super().__init__()
        self.state.authenticated = True

    def _authenticate(self) -> bool:
        """No authentication needed"""
        return True

    def _prepare(self, request: Request) -> Request:
        """No credentials to add"""
        return request
