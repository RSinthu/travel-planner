"""FastAPI entry point.

Run from backend/:  .venv/Scripts/uvicorn app.main:app --port 8080
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import make_url

from .config import ENV_FILE, Settings, get_settings

# The tools and agents read API keys and model names from the environment.
load_dotenv(ENV_FILE)

from google.adk.agents import BaseAgent  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import DatabaseSessionService  # noqa: E402

from .auth import jwks_client  # noqa: E402
from .errors import install_error_handlers  # noqa: E402
from .routes import system, trips  # noqa: E402
from .services.rate_limit import RateLimiter  # noqa: E402
from .services.trips import APP_NAME, TripService  # noqa: E402

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None, agent: BaseAgent | None = None) -> FastAPI:
    """Build the app. Tests pass their own settings and a fake agent."""
    settings = settings or get_settings()
    if agent is None:
        from travel_agent.agent import root_agent

        agent = root_agent

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        sessions = DatabaseSessionService(db_url=settings.database_url)
        await _check_database(sessions, settings.database_url)
        runner = Runner(app_name=APP_NAME, agent=agent, session_service=sessions)
        app.state.trips = TripService(runner, sessions, settings.max_llm_calls)
        app.state.rate_limiter = RateLimiter(settings.rate_limit_per_minute, settings.rate_limit_per_day)
        logger.info("Travel planner API started (%s)", settings.app_env)
        try:
            yield
        finally:
            await runner.close()
            await sessions.close()

    is_dev = settings.app_env == "development"
    app = FastAPI(
        title="Travel Planner API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if is_dev else None,
        redoc_url=None,
        openapi_url="/openapi.json" if is_dev else None,
    )
    app.state.settings = settings
    app.state.jwks = jwks_client(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("%s %s -> %d (%.0f ms) id=%s", request.method, request.url.path, response.status_code,
                    (time.perf_counter() - started) * 1000, request_id)
        return response

    install_error_handlers(app)
    app.include_router(system.router)
    app.include_router(trips.router)
    if is_dev:
        app.include_router(system.dev_router)
    return app


async def _check_database(sessions: DatabaseSessionService, url: str) -> None:
    """Fail at startup with a clear message instead of on the first request."""
    try:
        await sessions.list_sessions(app_name=APP_NAME, user_id="__startup_check__")
    except Exception as exc:
        safe_url = make_url(url).render_as_string(hide_password=True)
        await sessions.close()
        raise RuntimeError(
            f"Cannot use the database at {safe_url} ({type(exc).__name__}). "
            "Check DATABASE_URL in backend/.env, or leave it empty to use SQLite."
        ) from exc


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = create_app()
