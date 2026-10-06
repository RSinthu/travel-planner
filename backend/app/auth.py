"""JWT authentication.

Every trip call needs `Authorization: Bearer <token>`. The token's `sub` claim is
the user id, so users can only see their own trips. Two kinds of token work:

- Better Auth tokens from the frontend: signed with its private key (EdDSA) and
  checked against its public keys at AUTH_JWKS_URL, plus issuer and audience.
- HS256 tokens signed with JWT_SECRET: POST /api/auth/dev-token in development,
  and the tests.
"""

import re
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings
from .errors import ApiError

_bearer = HTTPBearer(auto_error=False)
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{1,128}$")
ASYMMETRIC_ALGORITHMS = ["EdDSA", "ES256", "RS256"]
_UNAUTHORIZED = {"WWW-Authenticate": "Bearer"}


def create_token(settings: Settings, user_id: str, minutes: int) -> str:
    now = datetime.now(UTC)
    claims = {"sub": user_id, "aud": settings.jwt_audience, "iat": now, "exp": now + timedelta(minutes=minutes)}
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def jwks_client(settings: Settings) -> jwt.PyJWKClient | None:
    """Fetches and caches the frontend's public keys (refetched when a new key id appears)."""
    if not settings.auth_jwks_url:
        return None
    return jwt.PyJWKClient(settings.auth_jwks_url, cache_keys=True, lifespan=3600, timeout=10)


def _decode(token: str, request: Request) -> dict:
    settings: Settings = request.app.state.settings
    algorithm = jwt.get_unverified_header(token).get("alg")
    required = {"require": ["exp", "sub", "aud"]}

    if algorithm == settings.jwt_algorithm:
        if not settings.jwt_secret:
            raise jwt.InvalidTokenError("HS256 tokens are disabled")
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
                          audience=settings.jwt_audience, options=required)

    keys: jwt.PyJWKClient | None = request.app.state.jwks
    if keys is None or algorithm not in ASYMMETRIC_ALGORITHMS:
        raise jwt.InvalidTokenError("unsupported token")
    try:
        signing_key = keys.get_signing_key_from_jwt(token)
    except jwt.PyJWKClientConnectionError as exc:
        raise ApiError(503, "auth_unavailable", "Sign-in can't be checked right now. Try again shortly.") from exc
    return jwt.decode(token, signing_key, algorithms=ASYMMETRIC_ALGORITHMS, audience=settings.auth_audience,
                      issuer=settings.auth_issuer, options={"require": ["exp", "sub", "aud", "iss"]})


def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> str:
    """FastAPI dependency: the user id from a valid bearer token, or 401.

    A plain `def`, so FastAPI runs it in a worker thread: fetching the public keys
    (rarely, they are cached) never blocks the event loop.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "not_authenticated", "Missing bearer token.", headers=_UNAUTHORIZED)
    try:
        claims = _decode(credentials.credentials, request)
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "token_expired", "The token has expired.", headers=_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        raise ApiError(401, "invalid_token", "The token is not valid.", headers=_UNAUTHORIZED)

    user_id = claims["sub"]
    if not isinstance(user_id, str) or not USER_ID_PATTERN.match(user_id):
        raise ApiError(401, "invalid_token", "The token's user id is not valid.", headers=_UNAUTHORIZED)
    return user_id


CurrentUser = Annotated[str, Depends(current_user)]
