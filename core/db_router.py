# core/db_router.py
import os
from contextvars import ContextVar
from typing import Literal

# Valore di default configurabile via env (DEFAULT_DB)
_DEFAULT_DB = os.getenv("DEFAULT_DB", "demo_restaurant")
_current_db: ContextVar[str] = ContextVar("_current_db", default=_DEFAULT_DB)

def map_project_to_db(project: str | None) -> str:
    """
    Regola di mapping:
    • 'sushi'/'demo' → database di default (DEFAULT_DB)
    • None / ''      → database di default
    • altrimenti     → lo stesso nome (es. 'pizza', 'messicano')
    """
    if not project:
        return _DEFAULT_DB
    normalized = project.lower()
    if normalized in ("sushi", "demo"):
        return _DEFAULT_DB
    return normalized

def set_current_db(project: str | None):
    """Va chiamata all’inizio di ogni request."""
    _current_db.set(map_project_to_db(project))

def get_current_db() -> str:
    """Da usare ovunque serva conoscere il DB corrente."""
    return _current_db.get()
