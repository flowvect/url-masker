"""Models package — re-exports all ORM models and the Base for Alembic."""

from app.models.base import Base
from app.models.user import User
from app.models.link import Link
from app.models.click import Click

__all__ = ["Base", "User", "Link", "Click"]
