# ~/clientfactory/auth/apikey.py
from __future__ import annotations
import typing as t
from dataclasses import dataclass
from enum import Enum
from clientfactory.auth.base import BaseAuth, AuthState, AuthError
from clientfactory.utils.request import Request

class ApiKeyLocation(str, Enum):
    """Where to place the API key in the request"""
    HEADER = "header"
    QUERY = "query"

@dataclass
class ApiKeyConfig:
    """Configuration for API key authentication"""
    key: str
    name: str = "X-Api-Key"  # Header name or query param name
    location: ApiKeyLocation = ApiKeyLocation.HEADER
    prefix: t.Optional[str] = None  # Optional prefix (e.g., "Bearer")

class ApiKeyAuth(BaseAuth):
    """
    API key authentication handler.
    Supports header-based or query parameter-based authentication.

    Examples:
        # Header-based (default)
        auth = ApiKeyAuth("my-api-key")  # Uses X-Api-Key header
        auth = ApiKeyAuth("my-api-key", name="Authorization", prefix="Bearer")

        # Query parameter-based
        auth = ApiKeyAuth("my-api-key", location="query", name="api_key")
    """

    def __init__(self,
                 key: str,
                 name: t.Optional[str] = None,
                 location: t.Optional[str | ApiKeyLocation] = None,
                 prefix: t.Optional[str] = None):
        """
        Initialize API key authentication.

        Args:
            key: The API key value
            name: Name of header or query parameter (default: X-Api-Key)
            location: Where to put the key - "header" or "query"
            prefix: Optional prefix for the key (e.g., "Bearer")
        """
        super().__init__()

        # Convert string location to enum
        if isinstance(location, str):
            try:
                location = ApiKeyLocation(location.lower())
            except ValueError:
                raise AuthError(
                    f"Invalid location '{location}'. Must be one of: "
                    f"{', '.join(x.value for x in ApiKeyLocation)}"
                )

        self.config = ApiKeyConfig(
            key=key,
            name=name or "X-Api-Key",
            location=location or ApiKeyLocation.HEADER,
            prefix=prefix
        )

    def authenticate(self) -> AuthState:
        """
        Validate and store API key.
        This is a simple implementation that just checks the key exists.
        """
        if not self.config.key:
            raise AuthError("API key cannot be empty")

        self.state.token = self.config.key
        self.state.authenticated = True
        return self.state

    def prepare(self, request: Request) -> Request:
        """Add API key to the request"""
        if not self.isauthenticated:
            self.authenticate()

        # Format key with optional prefix
        key = (
            f"{self.config.prefix} {self.config.key}"
            if self.config.prefix else
            self.config.key
        )

        if self.config.location == ApiKeyLocation.HEADER:
            # Add key to headers
            return request.WITH(
                headers={self.config.name: key}
            )
        else:
            # Add key to query parameters
            return request.WITH(
                params={self.config.name: key}
            )

    @classmethod
    def header(cls, key: str, name: str = "X-Api-Key", prefix: t.Optional[str] = None) -> ApiKeyAuth:
        """Convenience method for header-based auth"""
        return cls(key, name=name, location=ApiKeyLocation.HEADER, prefix=prefix)

    @classmethod
    def query(cls, key: str, name: str = "api_key") -> ApiKeyAuth:
        """Convenience method for query parameter-based auth"""
        return cls(key, name=name, location=ApiKeyLocation.QUERY)
