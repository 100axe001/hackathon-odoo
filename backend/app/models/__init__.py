"""Importing this package registers every model on Base.metadata.

SQLAlchemy resolves relationship targets by name at mapper-configuration time,
so a module that is never imported leaves its class unfindable - and the failure
surfaces far away, as an unrelated query blowing up. Import them all in one
place instead.
"""

from app.models import identity  # noqa: F401

__all__ = ["identity"]
