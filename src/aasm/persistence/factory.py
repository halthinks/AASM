from __future__ import annotations
from pathlib import Path
from .sqlite import SQLiteStore


def open_store(target:str):
    """Open SQLite or PostgreSQL storage from one target string."""
    if target.startswith(("postgres://","postgresql://")):
        from .postgres import PostgresStore
        return PostgresStore(target)
    if target.startswith("sqlite:///"): target=target[len("sqlite:///"):]
    return SQLiteStore(Path(target))
