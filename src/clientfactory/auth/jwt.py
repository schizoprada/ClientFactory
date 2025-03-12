# ~/ClientFactory/src/clientfactory/auth/jwt.py
from __future__ import annotations
import jwt as JWT, typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields, asdict
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
from loguru import logger as log


@dataclass
class JWK:
    """JSON Web Key representation"""
    kty: str  # Key Type (RSA, EC, etc)
    kid: t.Optional[str] = None  # Key ID
    use: t.Optional[str] = None  # Use (sig, enc)
    key_ops: t.Optional[list[str]] = None  # Key Operations
    alg: t.Optional[str] = None  # Algorithm
    ext: t.Optional[bool] = None  # Extractable flag

    # RSA specific
    n: t.Optional[str] = None  # Modulus
    e: t.Optional[str] = None  # Exponent

    # EC specific
    crv: t.Optional[str] = None  # Curve
    x: t.Optional[str] = None  # X coordinate
    y: t.Optional[str] = None  # Y coordinate
    d: t.Optional[str] = None  # Private key (if present)

    def __post_init__(self):
        match self.kty:
            case 'EC':
                if not all([self.crv, self.x, self.y]):
                    raise ValueError("JWK.__post_init__ | EC Keys require: [crv (curve), x (coordinate), y (coordinate)] params")
            case 'RSA':
                if not all([self.n, self.e]):
                    raise ValueError("JWK.__post_init__ | RSA keys require [n (modulus), e (exponent)] params")
            case _:
                raise ValueError(f"JWK.__post_init__ | Unsupported Encryption: {self.kty}")

        # Validate key operations if present
        if self.key_ops and not isinstance(self.key_ops, list):
            raise ValueError("JWK.__post_init__ | key_ops must be a list")

    @property
    def usage(self) -> t.Optional[str]:
        """Get key usage from either 'use' or 'key_ops'"""
        if self.use:
            return self.use
        if self.key_ops:
            # Map key_ops to use value
            if "sign" in self.key_ops:
                return "sig"
            if "encrypt" in self.key_ops:
                return "enc"
        return None

    @classmethod
    def fromdict(cls, data: dict) -> 'JWK':
        valid_fields = {f.name for f in fields(cls)}
        return cls(**{
            k: v for k, v in data.items()
            if k in valid_fields
        })

    def todict(self) -> dict:
        """Convert to dictionary, preserving optional fields"""
        return {
            k: v for k, v in asdict(self).items()
            if v is not None
        }

    def topublic(self) -> 'JWK':
        """Create public key by removing private components"""
        data = self.todict()
        data.pop('d', None)  # Remove private key
        return self.fromdict(data)

class TokenGenerator(ABC):
    """Base class for token generators"""

    @abstractmethod
    def generate(self, claims: dict) -> str:
        """Generate a token with given claims"""
        pass

    @abstractmethod
    def validate(self, token: str) -> dict:
        """Validate token and return claims"""
        pass


class JWTGenerator(TokenGenerator):
    """Standard JWT token generator"""
    def __init__(self, jwk: JWK):
        self.jwk = jwk
        self.privatekey = None
        self.publickey = None
        self._initkeys()

    def _initkeys(self):
        """Initialize keys based on JWK type"""
        try:
            match self.jwk.kty:
                case 'EC':
                    self._initeckeys()
                case 'RSA':
                    self._initrsakeys()
                case _:
                    raise ValueError(f"JWTGenerator._initkeys | Unsupported key type: {self.jwk.kty}")
        except Exception as e:
            log.error(f"JWTGenerator._initkeys | exception | {str(e)}")
            raise

    def _initrsakeys(self):
        """Initialize RSA keys from JWK"""
        import base64
        def toint(s: str) -> int:
            return int.from_bytes(
                base64.urlsafe_b64decode(s + '=' * (4 - len(s) % 4)),
                'big'
            )

        # RSA requires modulus (n) and exponent (e)
        assert (self.jwk.n and self.jwk.e), f"JWTGenerator._initrsakeys | RSA requires N (modulus) and E (exponent)"

        try:
            n = toint(self.jwk.n)
            e = toint(self.jwk.e)

            pubnums = rsa.RSAPublicNumbers(e, n)
            self.publickey = pubnums.public_key()

            if self.jwk.d:  # Private key components available
                # For RSA, we'll only support public key operations
                # since we don't have all prime factors
                log.warning("RSA private key operations not supported without prime factors")
                self.privatekey = None

        except Exception as e:
            log.error(f"JWTGenerator._initrsakeys | exception | {str(e)}")
            raise

    def _initeckeys(self):
        # Similar to DPOPGenerator key init but without P-256 restriction
        import base64
        def toint(s: str) -> int:
            return int.from_bytes(
                base64.urlsafe_b64decode(s + '=' * (4 - len(s) % 4)),
                'big'
            )

        x = toint(self.jwk.x)
        y = toint(self.jwk.y)
        pubnums = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())

        if self.jwk.d:
            d = toint(self.jwk.d)
            privnums = ec.EllipticCurvePrivateNumbers(d, pubnums)
            self.privatekey = privnums.private_key()
            self.publickey = self.privatekey.public_key()
        else:
            self.publickey = pubnums.public_key()

    def generate(self, claims: dict) -> str:
        """Generate standard JWT"""
        assert self.privatekey, f"JWTGenerator.generate | private key required for token generation"

        header = {
            'typ': 'jwt',
            'alg': self.jwk.alg or 'ES256'
        }

        claims.update({
            'iat': int(datetime.now(timezone.utc).timestamp())
        })

        return JWT.encode(
            claims,
            self.privatekey,
            algorithm=header['alg'],
            headers=header
        )

    def validate(self, token: str) -> dict:
        """Validate JWT"""
        try:
            return JWT.decode(
                token,
                self.publickey,
                algorithms=[self.jwk.alg or 'ES256']
            )
        except JWT.InvalidTokenError as e:
            log.error(f"JWTGenerator.validate | token validation exception | {str(e)}")
            raise

class DPOPGenerator(TokenGenerator):
    def __init__(self, jwk: JWK):
        if (jwk.kty != 'EC') or (jwk.crv != 'P-256'):
            raise ValueError(f"DPOPGenerator.__init__ | DPoP requires EC P-256 Key")
        self.jwk = jwk
        self.privatekey = None
        self.publickey = None
        self._initkeys()

    def _initkeys(self):
        """Initialize cryptographic keys from JWK"""
        import base64
        def toint(s: str) -> int:
            """base64url -> integer"""
            return int.from_bytes(
                base64.urlsafe_b64decode(s + '=' * (4 - len(s) % 4)),
                'big'
            )
        assert (self.jwk.x and self.jwk.y), f"DPOPGenerator._initkeys | DPoP requires X and Y coordinates"
        try:
            x = toint(self.jwk.x)
            y = toint(self.jwk.y)

            pubnums = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1())

            if self.jwk.d:
                d = toint(self.jwk.d)
                privnums = ec.EllipticCurvePrivateNumbers(d, pubnums)
                self.privatekey = privnums.private_key()
                self.publickey = self.privatekey.public_key()
            else:
                self.publickey = pubnums.public_key()
        except Exception as e:
            log.error(f"DPOPGenerator._initkeys | exception | {str(e)}")
            raise

    def generate(self, claims: dict) -> str:
        """Generate DPoP token"""
        assert self.privatekey, f"DPOPGenerator.generate | private key required for token generation"
        header = {
            'typ': 'dpop+jwt',
            'alg': 'ES256',
            'jwk': self.jwk.topublic().todict()
        }
        claims.update({
            'iat': int(datetime.now(timezone.utc).timestamp())
        })
        return JWT.encode(
            claims,
            self.privatekey,
            algorithm='ES256',
            headers=header
        )

    def validate(self, token: str) -> dict:
        """Validate DPoP token"""
        try:
            return JWT.decode(
                token,
                self.publickey,
                algorithms=['ES256']
            )
        except JWT.InvalidTokenError as e:
            log.error(f"DPOPGenerator.validate | token validation exception | {str(e)}")
            raise
