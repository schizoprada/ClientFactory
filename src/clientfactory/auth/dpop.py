# ~/ClientFactory/src/clientfactory/auth/dpop.py
"""
DPoP Authentication Module
---------------------------
Implements DPoP (Demonstration of Proof-of-Possession) token authentication.
"""
from __future__ import annotations
import base64, uuid, typing as t, traceback as tb
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from clientfactory.log import log

from clientfactory.core.request import Request
from clientfactory.auth.tokens import TokenAuth, TokenScheme, TokenError

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
            ecrequired = {'crv', 'x', 'y', 'd'}
            rsarequired = {'n', 'e', 'd'}
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

    def _generateEC(self, request: t.Optional[Request] = None) -> str:
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
            if request:
                payload['htu'] = request.url
                payload['htm'] = request.method.value

            if 'uuid' in self.jwk:
                payload['uuid'] = self.jwk['uuid']

            jwkheader = {
                'typ': 'dpop+jwt',
                'alg': self.jwk.get('alg', 'ES256'),
                'jwk': {
                    'crv': self.jwk.get('crv', 'P-256'),
                    'kty': self.jwk.get('kty', 'EC'),
                    'x': self.jwk.get('x'),
                    'y': self.jwk.get('y')
                }
            }

            return jwt.encode(
                payload,
                privatekey,
                algorithm=self.jwk.get('alg', 'ES256'),
                headers=jwkheader
            )
        except Exception as e:
            raise DpopError(f"Token generation failed: {e}", tb.format_exc())

    def _generatetoken(self, request: t.Optional[Request] = None) -> str:
        tokentype = self.jwk.get('kty')
        if not tokentype:
            raise DpopError("JWK missing kty field")
        if tokentype.lower() == 'ec':
            return self._generateEC(request)
        raise NotImplementedError(f"Token generation for ({tokentype}) DPoP tokens not yet implemented")

    def _authenticate(self) -> bool:
        try:
            token = self._generatetoken()
            self.updatetoken(token)
            return True
        except Exception as e:
            raise DpopError(f"Authentication failed: {e}")

    def _prepare(self, request: Request) -> Request:
        log.debug(f"DEBUGGING - DPoP Auth preparation:")
        log.debug(f"DEBUGGING - Self.headerkey: {self.headerkey}")
        log.debug(f"DEBUGGING - Self.jwk: {self.jwk}")
        try:
            request = super()._prepare(request)
            log.debug(f"DEBUGGING - Headers after super()._prepare: {request.headers}")
            token = self._generatetoken(request)
            log.debug(f"DEBUGGING - Generated token: {token[:30]}...")
            headers = dict(request.headers or {})
            headers[self.headerkey] = token
            log.debug(f"DEBUGGING - Final headers: {headers}")
            return request.clone(headers=headers)
        except Exception as e:
            log.debug(f"DEBUGGING - Error in DPoP._prepare: {str(e)}")
            raise

    @classmethod
    def FromDict(cls, jwk: dict, **kwargs) -> DpopAuth:
        return cls(jwk, **kwargs)
