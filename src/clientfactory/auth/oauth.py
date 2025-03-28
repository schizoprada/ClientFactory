# ~/ClientFactory/src/clientfactory/auth/oauth.py
"""
OAuth 2.0 Authentication Module
-------------------------------
Implements OAuth 2.0 authentication flows.
"""
from __future__ import annotations
import json, enum, typing as t, requests as rq
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from clientfactory.core import Request
from clientfactory.auth.base import BaseAuth, AuthError, AuthState
from clientfactory.auth.tokens import TokenAuth, TokenScheme

class OAuthError(AuthError):
    """Raised for OAuth related exceptions."""
    pass

@dataclass
class OAuthToken:
    """Represents an OAuth 2.0 token response"""
    accesstoken: str
    tokentype: TokenScheme
    expiresin: t.Optional[int] = None
    refreshtoken: t.Optional[str] = None
    scope: t.Optional[str] = None
    created: datetime = field(default_factory=datetime.now)

    @property
    def expired(self) -> bool:
        """Checl if the token has expired"""
        if self.expiresin is None:
            return False
        expiration = (self.created + timedelta(seconds=self.expiresin))
        return datetime.now() > expiration

class OAuthFlow(str, enum.Enum):
    CLIENTCREDENTIALS = "ClientCredentials"
    AUTHORIZATIONCODE = "AuthorizationCode"

@dataclass
class OAuthConfig:
    """Configuration for OAuth 2.0 authentication"""
    clientid: str
    clientsecret: str
    tokenurl: str
    authurl: t.Optional[str] = None
    redirecturi: t.Optional[str] = None
    scope: t.Optional[str] = None
    tokenfield: str = "access_token"
    flow: OAuthFlow = OAuthFlow.AUTHORIZATIONCODE
    extraparams: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)


class OAuthAuth(BaseAuth):
    """
    OAuth 2.0 Authentication provider.

    Supports various OAuth 2.0 flows including:
        - Client Credentials
        - Authorization Code
        - Refresh Token
    """

    __declarativetype__ = 'oauth'

    clientid: str = ""
    clientsecret: str = ""
    tokenurl: str = ""
    authurl: t.Optional[str] = None
    redirecturi: t.Optional[str] = None
    scope: t.Optional[str] = None
    tokenfield: str = "access_token"
    flow: OAuthFlow = OAuthFlow.AUTHORIZATIONCODE
    extraparams: dict = {}
    headers: dict = {}

    def __init__(self, config: t.Optional[OAuthConfig] = None, token: t.Optional[OAuthToken] = None, **kwargs):
        """Initialize with OAuth 2.0 configuration"""
        super().__init__(**kwargs)
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        if config is None:
            config = OAuthConfig(
                clientid=self.clientid,
                clientsecret=self.clientsecret,
                tokenurl=self.tokenurl,
                authurl=self.authurl,
                redirecturi=self.redirecturi,
                scope=self.scope,
                tokenfield=self.tokenfield,
                flow=self.flow,
                extraparams=self.extraparams,
                headers=self.headers
            )
        self.config = config
        self._token = token

        if token:
            self.state.token = token.accesstoken
            self.state.authenticated = True
            if token.expiresin:
                self.state.expires = (token.created + timedelta(seconds=token.expiresin))

    def _authenticate(self) -> bool:
        """Authenticate using client credentials flow."""
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.clientid,
            "client_secret": self.config.clientsecret
        }
        if self.config.scope:
            data['scope'] = self.config.scope

        data.update(self.config.extraparams)

        try:
            r = rq.post(
                self.config.tokenurl,
                data=data,
                headers=self.config.headers
            )
            r.raise_for_status()
            tokendata = r.json()
            self._token = OAuthToken(
                accesstoken=tokendata.get(self.config.tokenfield, ""),
                tokentype=TokenScheme(tokendata.get("token_type", "Bearer")),
                expiresin=(int(tokendata.get('expires_in')) if tokendata.get('expires_in') else None),
                refreshtoken=tokendata.get('refresh_token'),
                scope=tokendata.get('scope')
            )
            self.state.token = self._token.accesstoken
            if self._token.expiresin:
                self.state.expires = (datetime.now() + timedelta(seconds=self._token.expiresin))
            return bool(self._token.accesstoken)
        except Exception as e:
            raise OAuthError(f"OAuth2 authentication failed: {str(e)}")

    def _prepare(self, request: Request) -> Request:
        """Add OAuth 2.0 token to the request"""
        if (not self._token) or (not self._token.accesstoken):
            raise OAuthError(f"No OAuth2 token available")

        headers = dict(request.headers or {})
        tokentype = self._token.tokentype or TokenScheme("Bearer")
        headers['Authorization'] = f"{tokentype.value} {self._token.accesstoken}"

        return request.clone(headers=headers)


    def refresh(self) -> bool:
        """Refresh the OAuth 2.0 token."""
        if (not self._token) or (not self._token.refreshtoken):
            return self.authenticate()
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._token.refreshtoken,
            "client_id": self.config.clientid,
            "client_secret": self.config.clientsecret
        }
        try:
            r = rq.post(
                self.config.tokenurl,
                data=data,
                headers=self.config.headers
            )
            r.raise_for_status()
            tokendata = r.json()
            self._token = OAuthToken(
                accesstoken=tokendata.get(self.config.tokenfield, ""),
                tokentype=TokenScheme(tokendata.get("token_type", "Bearer")),
                expiresin=(int(tokendata.get('expires_in')) if tokendata.get('expires_in') else None),
                refreshtoken=tokendata.get('refresh_token'),
                scope=tokendata.get('scope')
            )
            self.state.token = self._token.accesstoken
            self.state.authenticated = True
            if self._token.expiresin:
                self.state.expires = (datetime.utcnow() + timedelta(seconds=self._token.expiresin))
            return bool(self._token.accesstoken)
        except Exception as e:
            self.state.authenticated = False
            raise OAuthError(f"OAuth2 token refresh failed: {str(e)}")
        return super().refresh()


    def authorizeurl(self, state: t.Optional[str] = None) -> str:
        """Get the authorization URL for the authorization code flow."""
        if not self.config.authurl:
            raise OAuthError(f"Authorization URL not configured")

        if not self.config.redirecturi:
            raise OAuthError(f"Redirect URI not configured")

        from urllib.parse import urlencode
        params = {
            "response_type": "code",
            "client_id": self.config.clientid,
            "redirect_uri": self.config.redirecturi
        }
        if self.config.scope:
            params["scope"] = self.config.scope
        if state:
            params["state"] = state
        return f"{self.config.authurl}?{urlencode(params)}"


    def exchangecode(self, code: str) -> bool:
        """Exchange an authorization code for a token."""
        if not self.config.redirecturi:
            raise OAuthError(f"Redirect URI not configured")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.config.clientid,
            "client_secret": self.config.clientsecret,
            "redirect_uri": self.config.redirecturi
        }
        try:
            r = rq.post(
                self.config.tokenurl,
                data=data,
                headers=self.config.headers
            )
            r.raise_for_status()
            tokendata = r.json()
            self._token = OAuthToken(
                accesstoken=tokendata.get(self.config.tokenfield, ""),
                tokentype=TokenScheme(tokendata.get("token_type", "Bearer")),
                expiresin=(int(tokendata.get('expires_in')) if tokendata.get('expires_in') else None),
                refreshtoken=tokendata.get('refresh_token'),
                scope=tokendata.get('scope')
            )
            self.state.token = self._token.accesstoken
            self.state.authenticated = True
            if self._token.expiresin:
                self.state.expires = (datetime.now() + timedelta(seconds=self._token.expiresin))
            return bool(self._token.accesstoken)
        except Exception as e:
            raise OAuthError(f"OAuth2 code exchange failed: {str(e)}")


    @classmethod
    def ClientCredentials(cls, clientid: str, clientsecret: str, tokenurl: str, scope: t.Optional[str] = None, **kwargs) -> OAuthAuth:
        """Create an OAuthAuth instance for client credentials flow."""
        config = OAuthConfig(
            clientid=clientid,
            clientsecret=clientsecret,
            tokenurl=tokenurl,
            scope=scope,
            flow=OAuthFlow.CLIENTCREDENTIALS,
            **kwargs
        )
        return cls(config)

    @classmethod
    def AuthorizationCode(cls, clientid: str, clientsecret: str, authurl: str, tokenurl: str, redirecturi: str, scope: t.Optional[str] = None, **kwargs) -> OAuthAuth:
        """Create an OAuthAuth instance for authorization code flow."""
        config = OAuthConfig(
            clientid=clientid,
            clientsecret=clientsecret,
            authurl=authurl,
            tokenurl=tokenurl,
            redirecturi=redirecturi,
            scope=scope,
            flow=OAuthFlow.AUTHORIZATIONCODE,
            **kwargs
        )
        return cls(config)
