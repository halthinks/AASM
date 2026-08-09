from __future__ import annotations

from .base import Store

__all__ = ["Store", "MemoryStore", "SQLiteStore", "PostgresStore", "open_store"]


def __getattr__(name: str):
    # `core.reducer` imports `persistence.serde`. Python initializes this package
    # first, so eagerly importing SQLite/PostgreSQL here would import the reducer
    # again while it is only partially initialized. Backend imports therefore
    # remain lazy while preserving the public `from aasm.persistence import ...`
    # API.
    if name == "MemoryStore":
        from .memory import MemoryStore
        return MemoryStore
    if name == "SQLiteStore":
        from .sqlite import SQLiteStore
        return SQLiteStore
    if name == "PostgresStore":
        from .postgres import PostgresStore
        return PostgresStore
    if name == "open_store":
        from .factory import open_store
        return open_store
    raise AttributeError(name)
