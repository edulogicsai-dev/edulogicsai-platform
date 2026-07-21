"""
JWT verification using Supabase's JWKS endpoint.
Supports both HS256 (legacy) and ES256 (current ECC keys).
Falls back to shared secret if JWKS URL is not configured.
"""

import jwt
from jwt import PyJWKClient


class InvalidTokenError(Exception):
    pass


class JWTVerifier:
    def __init__(self, secret: str = "", algorithm: str = "HS256", jwks_url: str = "") -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._jwks_client = PyJWKClient(jwks_url) if jwks_url else None

    def verify(self, token: str) -> str:
        """Returns the authenticated user_id (JWT 'sub' claim)."""
        try:
            if self._jwks_client:
                signing_key = self._jwks_client.get_signing_key_from_jwt(token)
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["ES256", "HS256"],
                    options={"verify_aud": False},
                )
            else:
                payload = jwt.decode(
                    token,
                    self._secret,
                    algorithms=[self._algorithm],
                    options={"verify_aud": False},
                )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("token has no 'sub' claim")
        return user_id
