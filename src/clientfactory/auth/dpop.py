# ~/ClientFactory/src/clientfactory/auth/dpop.py
"""
DPoP Authentication Module
---------------------------
Implements DPoP (Demonstration of Proof-of-Possession) token authentication.
"""
from __future__ import annotations
import base64, uuid, typing as t
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from loguru import logger as log

from clientfactory.core.request import Request
from clientfactory.auth.token import TokenAuth, TokenScheme, TokenError

import jwt

class DpopError(TokenError):
    """Raised for DPoP-specific authentication errors"""
    pass

class DpopAuth(TokenAuth):
    """
    DPoP Authentication provider.

    Implements DPoP token generation and request signing using JWK keys.
    Automatically handles token generation and header preparation.
    """
    __declarativetype__ = 'dpop'
    headerkey = 'dpop'
    scheme = TokenScheme.JWT
    jwk: dict = {}

    def __init__(self, jwk: t.Optional[dict] = None, **kwargs):
        super().__init__(**kwargs)
        if jwk is not None:
            self.jwk = jwk
        self._validatetokenfields(self.jwk)

    def _validatetokenfields(self, token: dict):
        tokentype = token.get('kty')
        if tokentype:
            if tokentype.lower() not in (supportedtypes:={'ec', 'rsa'}):
                raise DpopError(f"Unsupported DPoP token type ({tokentype}) - supported: {supportedtypes}")
            ecrequired = {'n', 'e', 'd'}
            rsarequired = {'crv', 'x', 'y', 'd'}
            if tokentype.lower() == 'ec':
                if not all(k in token for k in ecrequired):
                    missing = [k for k in ecrequired if k not in token]
                    raise DpopError(f"EC DPoP token missing required field(s): {missing} - EC DPoP requires all of: {ecrequired}")
            if tokentype.lower() == 'rsa':
                if not all(k in token for k in rsarequired):
                    missing = [k for k in rsarequired if k not in token]
                    raise DpopError(f"RSA DPoP token missing required field(s): {missing} - RSA DPoP requires all of: {rsarequired}")
        else:
            raise DpopError(f"DPoP tokens must specify encryption type in 'kty' key")

    def _generateEC(self) -> str:
        try:
            privatevalue = base64.urlsafe_b64decode(
                self.jwk['d'] + '=' * (4 - len(self.jwk['d']) % 4)
            )
            privatekey = ec.derive_private_key(
                int.from_bytes(privatevalue, 'big'),
                ec.SECP256R1()
            )
            payload = {
                'iat': int(datetime.now(timezone.utc).timestamp()),
                'jti': str(uuid.uuid4())
            }
            return jwt.encode(
                payload,
                privatekey,
                algorithm=self.jwk.get('alg', 'ES256'),
                headers={'typ': 'dpop+jwt'}
            )
        except Exception as e:
            raise DpopError(f"Token generation failed: {e}")

    def _generatetoken(self) -> str:
        tokentype = self.jwk.get('kty')
        if not tokentype:
            raise DpopError("JWK missing kty field")
        if tokentype.lower() == 'ec':
            return self._generateEC()
        raise NotImplementedError(f"Token generation for ({tokentype}) DPoP tokens not yet implemented")

    def _authenticate(self) -> bool:
        try:
            token = self._generatetoken()
            self.updatetoken(token)
            return True
        except Exception as e:
            raise DpopError(f"Authentication failed: {e}")

    def _prepare(self, request: Request) -> Request:
        request = super()._prepare(request)
        token = self._generatetoken()
        headers = dict(request.headers or {})
        headers[self.headerkey] = token
        return request.clone(headers=headers)

    @classmethod
    def FromDict(cls, jwk: dict, **kwargs) -> DpopAuth:
        return cls(jwk, **kwargs)
