"""Health checks and the development-only token endpoint."""

from fastapi import APIRouter, Request

from ..auth import create_token
from ..errors import ApiError
from ..schemas import DevTokenIn, TokenOut
from ..services.trips import APP_NAME

router = APIRouter(prefix="/api", tags=["system"])
dev_router = APIRouter(prefix="/api/auth", tags=["development"])


@router.get("/health")
async def health():
    """Liveness: the process is up."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request):
    """Readiness: the database answers."""
    try:
        await request.app.state.trips.sessions.list_sessions(app_name=APP_NAME, user_id="__healthcheck__")
    except Exception as exc:
        raise ApiError(503, "database_unavailable", "The database is not reachable.") from exc
    return {"status": "ready"}


@dev_router.post("/dev-token", response_model=TokenOut)
async def dev_token(request: Request, body: DevTokenIn):
    """Issue a token for any user id. Only exists when APP_ENV=development."""
    settings = request.app.state.settings
    token = create_token(settings, body.user_id, settings.dev_token_minutes)
    return TokenOut(access_token=token, expires_in=settings.dev_token_minutes * 60)
