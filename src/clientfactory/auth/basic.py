# ~/ClientFactory/src/clientfactory/auth/basic.py
"""
Basic Authentication Module
---------------------------
Implements HTTP Basic Authentication.
"""
from __future__ import annotations
import base64, typing as t

from clientfactory.core import Request
from clientfactory.auth.base import BaseAuth, AuthError

class BasicAuth(BaseAuth):
    """
    HTTP Basic Authentication provider.

    Adds an Authorization header with the username and password encoded in the Basic authentication scheme.
    """
    __declarativetype__ = 'basicauth'
    username: str = ""
    password: str = ""

    def __init__(self, username: t.Optional[str] = None, password: t.Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password

    def _authenticate(self) -> bool:
        """
        Validate credentials.

        For Basic Auth we just check that username and password are provided
        """
        if (not self.username) or (not self.password):
            raise AuthError(f"Username and password are required")
        return True

    def _prepare(self, request: Request) -> Request:
        """
        Add Basic Auth header to the request.
        """
        authstr = f"{self.username}:{self.password}"
        authbytes = authstr.encode('utf-8')
        encoded = base64.b64encode(authbytes).decode('utf-8')

        headers = dict(request.headers or {})
        headers['Authorization'] = f"Basic {encoded}"
        return request.clone(headers=headers)


    @classmethod
    def FromURL(cls, url:str) -> BasicAuth:
        """
        Create a BasicAuth instance from a URL with embedded credentials.
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.username and parsed.password:
                return cls(parsed.username, parsed.password)
            raise AuthError(f"URL does not contain credentials")
        except Exception as e:
            raise AuthError(f"Failed to extract credentials from URL: {e}")
