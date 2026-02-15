from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_engine(database_url: str):
    connect_args = {}
    # SQLite thread setting (FastAPI)
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, echo=False, future=True, connect_args=connect_args)


def get_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
