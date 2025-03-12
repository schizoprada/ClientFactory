# ~/ClientFactory/src/clientfactory/auth/tests/test_jwt.py
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock
from clientfactory.auth.jwt import JWK, JWTGenerator, DPOPGenerator
from clientfactory.auth.base import JWTAuth, DPOPAuth, AuthError
from clientfactory.utils import Request, RequestMethod

class TestJWT:
    # Test vectors
    EC_JWK = {
        "kty": "EC",
        "crv": "P-256",
        "alg": "ES256",
        "x": "-JLE_wNMMbbyBIUz0jjBhEmO7I6A8jaLUM9oU04iATg",
        "y": "MvQlyk9gOG0JjVx3hX4LSeEF0FEL2VFiFRrIXAEz_r4",
        "d": "-cSeKcWDAx7WIQ8UpxAS9nntjWo8_jCuYk38n8wKJFM"
    }

    RSA_JWK = {
        "kty": "RSA",
        "alg": "RS256",
        "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
        "e": "AQAB",
        "d": "X4cTteJY_gn4FYPsXB8rdXix5vwsg1FLN5E3EaG6RJoVH-HLLKD9M7dx5oo7GURknchnrRweUkC7hT5fJLM0WbFAKNLWY2vv7B6NqXSzUvxT0_YSfqijwp3RTzlBaCxWp4doFk5N2o8Gy_nHNKroADIkJ46pRUohsXywbReAdYaMwFs9tv8d_cPVY3i07a3t8MN6TNwm0dSawm9v47UiCl3Sk5ZiG7xojPLu4sbg1U2jx4IBTNBznbJSzFHK66jT8bgkuqsk0GjskDJk19Z4qwjwbsnn4j2WBii3RL-Us2lGVkY8fkFzme1z0HbIkfz0Y6mqnOYtqc0X4jfcKoAC8Q"
    }

    def test_jwt_auth_init(self):
        # Test with EC key
        ec_jwk = JWK.fromdict(self.EC_JWK)
        jwt_auth = JWTAuth(ec_jwk)
        assert jwt_auth.scheme == "Bearer"
        assert jwt_auth.generator is not None
        assert jwt_auth.state.metadata['jwk'] == ec_jwk.todict()

        # Test with RSA key - should only support public key operations
        rsa_jwk = JWK.fromdict(self.RSA_JWK)
        jwt_auth = JWTAuth(rsa_jwk)
        assert jwt_auth.generator is not None
        assert jwt_auth.generator.publickey is not None
        assert jwt_auth.generator.privatekey is None  # No private key ops for RSA

    def test_jwt_auth_prepare(self):
        jwk = JWK.fromdict(self.EC_JWK)
        jwt_auth = JWTAuth(jwk)

        request = Request(
            method=RequestMethod.GET,
            url="https://api.example.com/test"
        )

        prepared = jwt_auth.prepare(request)
        assert "Authorization" in prepared.headers
        assert prepared.headers["Authorization"].startswith("Bearer ")

        # Verify token can be decoded
        token = prepared.headers["Authorization"].split(" ")[1]
        decoded = jwt_auth.generator.validate(token)
        assert "iat" in decoded
        assert "jti" in decoded

    def test_dpop_auth_init(self):
        jwk = JWK.fromdict(self.EC_JWK)
        dpop_auth = DPOPAuth(jwk)
        assert dpop_auth.scheme == "dpop"
        assert dpop_auth.generator is not None

        # Should fail with RSA key
        rsa_jwk = JWK.fromdict(self.RSA_JWK)
        with pytest.raises(ValueError):
            DPOPAuth(rsa_jwk)

    def test_dpop_auth_prepare(self):
        jwk = JWK.fromdict(self.EC_JWK)
        dpop_auth = DPOPAuth(jwk)

        request = Request(
            method=RequestMethod.POST,
            url="https://api.example.com/test"
        )

        prepared = dpop_auth.prepare(request)
        assert "dpop" in prepared.headers

        # Verify DPoP token
        token = prepared.headers["dpop"]
        decoded = dpop_auth.generator.validate(token)
        assert decoded["htm"] == "POST"
        assert decoded["htu"] == "https://api.example.com/test"

    def test_auth_error_handling(self):
        # Test with missing JWK
        with pytest.raises(AuthError):
            jwt_auth = JWTAuth(None)
            request = Request(
                method=RequestMethod.GET,
                url="https://api.example.com/test"
            )
            jwt_auth.prepare(request)

        # Test with invalid generator
        with pytest.raises(AuthError):
            dpop_auth = DPOPAuth(JWK.fromdict(self.EC_JWK))
            dpop_auth.generator = None
            request = Request(
                method=RequestMethod.GET,
                url="https://api.example.com/test"
            )
            dpop_auth.prepare(request)

    def test_token_validation(self):
        jwk = JWK.fromdict(self.EC_JWK)
        jwt_auth = JWTAuth(jwk)
        dpop_auth = DPOPAuth(jwk)

        # Test JWT token
        jwt_request = Request(
            method=RequestMethod.GET,
            url="https://api.example.com/test"
        )
        jwt_prepared = jwt_auth.prepare(jwt_request)
        jwt_token = jwt_prepared.headers["Authorization"].split(" ")[1]
        jwt_decoded = jwt_auth.generator.validate(jwt_token)
        assert isinstance(jwt_decoded, dict)

        # Test DPoP token
        dpop_request = Request(
            method=RequestMethod.POST,
            url="https://api.example.com/test"
        )
        dpop_prepared = dpop_auth.prepare(dpop_request)
        dpop_token = dpop_prepared.headers["dpop"]
        dpop_decoded = dpop_auth.generator.validate(dpop_token)
        assert isinstance(dpop_decoded, dict)
