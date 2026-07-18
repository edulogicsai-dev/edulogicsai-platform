"""
JWT verification -- secret is a constructor parameter, so swapping in
Supabase's real signing key later is a config change, not a code change.
A test secret is used in this change (epic Requirements Discovery). See
changes/2026/07/17/nexus-orchestration/changes/sse-endpoint/SPEC.md FR2.
"""

import jwt


class InvalidTokenError(Exception):
    pass


class JWTVerifier:
    def __init__(self, secret: str, algorithm: str = "HS256") -> None:
        self._secret = secret
        self._algorithm = algorithm

    def verify(self, token: str) -> str:
        """Returns the authenticated user_id (JWT 'sub' claim), or raises InvalidTokenError."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("token has no 'sub' claim")
        return user_id
