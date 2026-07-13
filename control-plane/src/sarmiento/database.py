from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def build_engine(database_url: str) -> Engine:
    kwargs: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **kwargs)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
    finally:
        session.close()
