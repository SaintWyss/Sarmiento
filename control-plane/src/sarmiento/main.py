from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import text

from . import __version__
from .api import router
from .config import Settings, get_settings
from .database import build_engine, build_session_factory, create_schema
from .rate_limit import SlidingWindowRateLimitMiddleware
from .services import DomainError, bootstrap_owner


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    if app_settings.environment.lower() == "production":
        if app_settings.owner_password == "change-me-now":
            raise RuntimeError("Set SARMIENTO_OWNER_PASSWORD before starting production")
        if app_settings.session_secret.startswith("development-secret"):
            raise RuntimeError("Set SARMIENTO_SESSION_SECRET before starting production")

    engine = build_engine(app_settings.database_url)
    session_factory = build_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
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
    )

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
