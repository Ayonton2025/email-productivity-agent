"""The single SQLAlchemy registry and metadata for all application models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
