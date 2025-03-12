# ~/clientfactory/auth/base.py
from __future__ import annotations
import uuid, typing as t
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from dataclasses import dataclass, field
from clientfactory.utils.request import Request
from clientfactory.utils.response import Response
from clientfactory.auth.jwt import JWK, DPOPGenerator, JWTGenerator

class AuthError(Exception):
    """Base exception for authentication errors"""
    pass

@dataclass
class AuthState:
    """Represents the current state of authentication"""
    authenticated: bool = False
    token: t.Optional[str] = None
    expires: t.Optional[float] = None
    metadata: dict = field(default_factory=dict)

class BaseAuth(ABC):
    """
    Base authentication handler.
    Defines interface for different auth methods.
    """
    def __init__(self):
        self.state = AuthState()

    @abstractmethod
    def authenticate(self) -> AuthState:
        """
        Perform initial authentication.
        Should set and return AuthState.
        """
        pass

    @abstractmethod
    def prepare(self, request: Request) -> Request:
        """
        Add authentication to request.
        e.g., add tokens, keys, signatures etc.
        """
        pass

    def handle(self, response: Response) -> Response:
        """
        Process response, handle auth-related errors.
        Default implementation just checks status.
        """
        if response.status_code == 401:
            self.state.authenticated = False
            raise AuthError("Authentication failed")
        elif response.status_code == 403:
            raise AuthError("Not authorized")
        return response

    def refresh(self) -> bool:
        """
        Refresh authentication if supported.
        Returns True if refresh was successful.
        Default implementation does nothing.
        """
        return False

    @property
    def isauthenticated(self) -> bool:
        """Check if currently authenticated"""
        return self.state.authenticated

    def __call__(self, request: Request) -> Request:
        """
        Convenience method to prepare requests.
        Allows auth to be used as a callable.
        """
        return self.prepare(request)

class NoAuth(BaseAuth):
    """Authentication handler for APIs that don't require auth"""

    def authenticate(self) -> AuthState:
        self.state.authenticated = True
        return self.state

    def prepare(self, request: Request) -> Request:
        return request

class TokenAuth(BaseAuth):
    """Simple token-based authentication"""

    def __init__(self, token: str, scheme: str = "Bearer"):
        super().__init__()
        self.token = token
        self.scheme = scheme
        self.state.token = token

    def authenticate(self) -> AuthState:
        self.state.authenticated = bool(self.token)
        return self.state

    def prepare(self, request: Request) -> Request:
        if not self.token:
            raise AuthError("No token provided")

        return request.WITH(
            headers={"Authorization": f"{self.scheme} {self.token}"}
        )

class BasicAuth(BaseAuth):
    """Basic authentication using username/password"""

    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password

    def authenticate(self) -> AuthState:
        self.state.authenticated = bool(self.username and self.password)
        return self.state

    def prepare(self, request: Request) -> Request:
        if not (self.username and self.password):
            raise AuthError("Username and password required")

        import base64
        auth = base64.b64encode(
            f"{self.username}:{self.password}".encode()
        ).decode()

        return request.WITH(
            headers={"Authorization": f"Basic {auth}"}
        )

class JWTAuth(BaseAuth):
    """JWT-based authentication"""
    def __init__(self, jwk: JWK, scheme: str = "Bearer"):
        super().__init__()
        if not jwk:
            raise AuthError("JWTAuth.__init__ | No JWK provided")
        self.jwk = jwk
        self.scheme = scheme
        self.generator = JWTGenerator(jwk)
        self.state.metadata['jwk'] = jwk.todict()

    def authenticate(self) -> AuthState:
        self.state.authenticated = bool(self.jwk)
        return self.state

    def prepare(self, request: Request) -> Request:
        if not self.generator:
            raise AuthError("JWTAuth.prepare | No JWT generator configured")

        token = self.generator.generate({
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "jti": str(uuid.uuid4())
        })

        return request.WITH(headers={
            "Authorization": f"{self.scheme} {token}"
        })


class DPOPAuth(JWTAuth):
    """DPoP authentication using EC P-256 keys"""
    def __init__(self, jwk: JWK):
        super().__init__(jwk, scheme="dpop")
        self.generator = DPOPGenerator(jwk)

    def prepare(self, request: Request) -> Request:
        if not self.generator:
            raise AuthError(f"DPOPAuth.prepare | No DPoP generator configured")
        return request.WITH(headers={
            "dpop": self.generator.generate({
                "htu": request.url,
                "htm": request.method.value
            })
        })
