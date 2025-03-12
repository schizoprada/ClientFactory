# ~/clientfactory/auth/oauth.py
from __future__ import annotations
import typing as t
from dataclasses import dataclass, field
from time import time
import requests
from urllib.parse import urlencode
from clientfactory.utils.request import RequestMethod
from clientfactory.auth.base import BaseAuth, AuthState, AuthError

@dataclass
class OAuth2Config:
    """Configuration for OAuth2 authentication"""
    clientid: str
    clientsecret: str
    tokenurl: str
    authurl: t.Optional[str] = None
    scope: t.Optional[str] = None
    redirecturi: t.Optional[str] = None
    tokenplacement: str = "header"  # header, query, body
    tokenprefix: str = "Bearer"
    extras: dict = field(default_factory=dict)  # Additional parameters for token requests

@dataclass
class OAuth2Token:
    """OAuth2 token information"""
    accesstoken: str
    tokentype: str
    expiresin: t.Optional[int] = None
    refreshtoken: t.Optional[str] = None
    scope: t.Optional[str] = None
    createdat: float = field(default_factory=time)

    @property
    def expired(self) -> bool:
        """Check if token has expired"""
        if not self.expiresin:
            return False
        return time() > self.createdat + self.expiresin

class OAuth2Auth(BaseAuth):
    """
    OAuth2 authentication handler supporting multiple grant types.

    Usage:
        # Client credentials flow
        auth = OAuth2Auth.clientcredentials(
            clientid="id",
            clientsecret="secret",
            tokenurl="https://api.example.com/oauth/token"
        )

        # Authorization code flow
        auth = OAuth2Auth.authorizationcode(
            clientid="id",
            clientsecret="secret",
            authurl="https://api.example.com/oauth/authorize",
            tokenurl="https://api.example.com/oauth/token",
            redirecturi="http://localhost:8080/callback"
        )
    """

    def __init__(self, config: OAuth2Config):
        super().__init__()
        self.config = config
        self._token: t.Optional[OAuth2Token] = None

    @classmethod
    def clientcredentials(cls,
                         clientid: str,
                         clientsecret: str,
                         tokenurl: str,
                         **kwargs) -> OAuth2Auth:
        """Create auth handler for client credentials flow"""
        config = OAuth2Config(
            clientid=clientid,
            clientsecret=clientsecret,
            tokenurl=tokenurl,
            **kwargs
        )
        return cls(config)

    @classmethod
    def authorizationcode(cls,
                         clientid: str,
                         clientsecret: str,
                         authurl: str,
                         tokenurl: str,
                         redirecturi: str,
                         **kwargs) -> OAuth2Auth:
        """Create auth handler for authorization code flow"""
        config = OAuth2Config(
            clientid=clientid,
            clientsecret=clientsecret,
            authurl=authurl,
            tokenurl=tokenurl,
            redirecturi=redirecturi,
            **kwargs
        )
        return cls(config)

    def getauthurl(self, state: t.Optional[str] = None) -> str:
        """Get authorization URL for code flow"""
        if not self.config.authurl:
            raise AuthError("Authorization URL not configured")

        params = {
            "clientid": self.config.clientid,
            "response_type": "code",
            "redirecturi": self.config.redirecturi,
        }

        if self.config.scope:
            params["scope"] = self.config.scope
        if state:
            params["state"] = state

        return f"{self.config.authurl}?{urlencode(params)}"

    def authenticate(self) -> AuthState:
        """Authenticate using client credentials flow"""
        data = {
            "grant_type": "clientcredentials",
            "clientid": self.config.clientid,
            "clientsecret": self.config.clientsecret,
        }

        if self.config.scope:
            data["scope"] = self.config.scope

        # Add any extra parameters
        data.update(self.config.extras)

        try:
            response = requests.post(self.config.tokenurl, data=data)
            response.raise_for_status()
            token_data = response.json()

            self._token = OAuth2Token(
                accesstoken=token_data["accesstoken"],
                tokentype=token_data.get("tokentype", "Bearer"),
                expiresin=token_data.get("expiresin"),
                refreshtoken=token_data.get("refreshtoken"),
                scope=token_data.get("scope")
            )

            self.state.authenticated = True
            self.state.token = self._token.accesstoken
            self.state.expires = self._token.createdat + (self._token.expiresin or 0)

            return self.state

        except requests.RequestException as e:
            raise AuthError(f"Authentication failed: {str(e)}")

    def authwithcode(self, code: str) -> AuthState:
        """Exchange authorization code for tokens"""
        if not self.config.redirecturi:
            raise AuthError("Redirect URI not configured")

        data = {
            "grant_type": "authorizationcode",
            "code": code,
            "clientid": self.config.clientid,
            "clientsecret": self.config.clientsecret,
            "redirecturi": self.config.redirecturi
        }

        try:
            response = requests.post(self.config.tokenurl, data=data)
            response.raise_for_status()
            return self.__handle__(response)

        except requests.RequestException as e:
            raise AuthError(f"Code exchange failed: {str(e)}")

    def refresh(self) -> bool:
        """Refresh access token using refresh token"""
        if not self._token or not self._token.refreshtoken:
            return False

        data = {
            "grant_type": "refreshtoken",
            "refreshtoken": self._token.refreshtoken,
            "clientid": self.config.clientid,
            "clientsecret": self.config.clientsecret,
        }

        try:
            response = requests.post(self.config.tokenurl, data=data)
            response.raise_for_status()
            self.__handle__(response)
            return True

        except requests.RequestException:
            return False

    def prepare(self, request: "Request") -> "Request":  # type: ignore
        """Add token to request based on configuration"""
        if not self._token:
            raise AuthError("Not authenticated")

        if self._token.expired and not self.refresh():
            raise AuthError("Token expired and refresh failed")

        token = f"{self.config.tokenprefix} {self._token.accesstoken}"

        if self.config.tokenplacement == "header":
            return request.WITH(headers={"Authorization": token})
        elif self.config.tokenplacement == "query":
            return request.WITH(params={"accesstoken": self._token.accesstoken})
        elif self.config.tokenplacement == "body":
            # Don't add to body for GET requests
            if request.method == RequestMethod.GET:
                return request.WITH(params={"accesstoken": self._token.accesstoken})

            if request.json is not None:
                data = {**request.json, "accesstoken": self._token.accesstoken}
                return request.WITH(json=data)
            elif request.data is not None:
                data = {**request.data, "accesstoken": self._token.accesstoken}
                return request.WITH(data=data)
            else:
                return request.WITH(data={"accesstoken": self._token.accesstoken})
        else:
            raise AuthError(f"Invalid token placement: {self.config.tokenplacement}")

    def __handle__(self, response: requests.Response) -> AuthState:
        """Process token response and update state"""
        token_data = response.json()

        self._token = OAuth2Token(
            accesstoken=token_data["accesstoken"],
            tokentype=token_data.get("tokentype", "Bearer"),
            expiresin=token_data.get("expiresin"),
            refreshtoken=token_data.get("refreshtoken", self._token.refreshtoken if self._token else None),
            scope=token_data.get("scope")
        )

        self.state.authenticated = True
        self.state.token = self._token.accesstoken
        self.state.expires = self._token.createdat + (self._token.expiresin or 0)

        return self.state
