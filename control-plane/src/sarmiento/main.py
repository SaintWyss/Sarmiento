from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .api import router
from .config import Settings, get_settings
from .database import build_engine, build_session_factory, create_schema
from .middleware import MaxRequestBodyMiddleware
from .rate_limit import SlidingWindowRateLimitMiddleware
from .services import DomainError, bootstrap_owner


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    if app_settings.environment.lower() == "production":
        if app_settings.session_secret.startswith("development-secret"):
            raise RuntimeError("Set SARMIENTO_SESSION_SECRET before starting production")
        if not app_settings.token_pepper:
            raise RuntimeError("Set an independent SARMIENTO_TOKEN_PEPPER in production")
        parsed_public_url = urlparse(app_settings.public_base_url)
        local_host = parsed_public_url.hostname in {"localhost", "127.0.0.1", "::1"}
        if not local_host and not app_settings.cookie_secure:
            raise RuntimeError("SARMIENTO_COOKIE_SECURE must be true in production")
        if not local_host and parsed_public_url.scheme.lower() != "https":
            raise RuntimeError("SARMIENTO_PUBLIC_BASE_URL must use HTTPS in production")

    engine = build_engine(app_settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if app_settings.environment.lower() != "production":
            create_schema(engine)
        with session_factory() as session:
            bootstrap_owner(session, app_settings)
        yield
        engine.dispose()

    app = FastAPI(
        title="Sarmiento Control Plane",
        version=__version__,
        docs_url="/api/docs" if app_settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = app_settings
    app.state.engine = engine
    app.state.session_factory = session_factory

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=app_settings.hosts)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Sarmiento-CSRF"],
    )
    app.add_middleware(
        SlidingWindowRateLimitMiddleware,
        default_per_minute=app_settings.rate_limit_per_minute,
        login_per_minute=app_settings.login_rate_limit_per_minute,
        max_buckets=app_settings.max_rate_limit_buckets,
    )
    app.add_middleware(MaxRequestBodyMiddleware, max_bytes=app_settings.max_request_body_bytes)

    @app.middleware("http")
    async def api_no_store(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError):
        del request
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "version": __version__}

    @app.get("/readyz")
    def readyz():
        with session_factory() as session:
            session.execute(text("SELECT 1"))
        return {"status": "ready"}

    app.include_router(router)

    agent_dir = Path(app_settings.agent_dir)
    if agent_dir.is_dir():
        app.mount("/agent", StaticFiles(directory=agent_dir), name="agent")

    viewer_dir = Path(app_settings.viewer_dir)
    if viewer_dir.is_dir():
        app.mount("/viewer", StaticFiles(directory=viewer_dir), name="viewer")

    static_dir = Path(app_settings.static_dir)
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="front")

    return app


app = create_app()
