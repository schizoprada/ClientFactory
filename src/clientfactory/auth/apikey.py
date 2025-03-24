# ~/ClientFactory/src/clientfactory/auth/apikey.py
"""
API Key Authentication Module
-----------------------------
Implements API key based authentication.
"""
from __future__ import annotations
import enum, typing as t

from clientfactory.core import Request
from clientfactory.auth.base import BaseAuth, AuthError

class KeyLocation(str, enum.Enum):
    """Locations where an API key can be placed"""
    HEADER = "header"
    QUERY = "query"
    COOKIE = "cookie"

class APIKeyError(AuthError):
    """Raised for API Key related exceptions"""
    pass

class APIKeyAuth(BaseAuth):
    """
    API Key Authentication provider.

    Supports adding API keys in headers, query parameters, or cookies.
    """

    def __init__(self, key: str, name: str = "X-API-Key", location: (str | KeyLocation) = KeyLocation.HEADER, prefix: t.Optional[str] = None):
        """Initialize with API key."""
        super().__init__()
        self.key = key
        self.name = name
        self.location = self._getlocation(location)
        self.prefix = prefix

    def _getlocation(self, location: (str | KeyLocation)) -> KeyLocation:
        if isinstance(location, KeyLocation):
            return location

        if isinstance(location, str):
            try:
                return KeyLocation(location.lower())
            except ValueError:
                raise APIKeyError(
                    f"Invalid API Key Location '{location}'. Must be one of:"
                    f"{', '.join(e.value for e in KeyLocation)}"
                )

    def _authenticate(self) -> bool:
        """
        Validate key existence.

        For API Key Auth we just check that a key is provided.
        """
        if not self.key:
            raise APIKeyError("API Key is required")
        self.state.token = self.key
        return True

    def _prepare(self, request: Request) -> Request:
        """Add API key to the request."""
        formattedkey = f"{self.prefix} {self.key}" if self.prefix else self.key

        if self.location == KeyLocation.HEADER:
            headers = dict(request.headers or {})
            headers[self.name] = formattedkey
            return request.clone(headers=headers)

        elif self.location == KeyLocation.QUERY:
            params = dict(request.params or {})
            params[self.name] = formattedkey
            return request.clone(params=params)

        elif self.location == KeyLocation.COOKIE:
            cookies = dict(request.cookies or {})
            cookies[self.name] = formattedkey
            return request.clone(cookies=cookies)
        else:
            raise APIKeyError(f"Unsupported API Key location: '{self.location}'")

    @classmethod
    def Header(cls, key: str, name: str = "X-API-Key", prefix: t.Optional[str] = None) -> APIKeyAuth:
        """Create an API Key Auth that adds the key to a header."""
        return cls(key, name, KeyLocation.HEADER, prefix)

    @classmethod
    def Query(cls, key: str, name: str = "X-API-Key", prefix: t.Optional[str] = None) -> APIKeyAuth:
        """Create an API Key Auth that adds the key to a query parameter."""
        return cls(key, name, KeyLocation.QUERY, prefix)

    @classmethod
    def Cookie(cls, key: str, name: str = "X-API-Key", prefix: t.Optional[str] = None) -> APIKeyAuth:
        """Create an API Key Auth that adds the key to a cookie."""
        return cls(key, name, KeyLocation.COOKIE, prefix)
