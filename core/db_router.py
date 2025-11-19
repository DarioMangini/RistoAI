# core/db_router.py
from contextvars import ContextVar
from typing import Literal

# Valore di default: ristosushi_it
_current_db: ContextVar[str] = ContextVar("_current_db",
                                          default="ristosushi_it")

def map_project_to_db(project: str | None) -> str:
    """
    Regola di mapping:
    • 'sushi'      → 'ristosushi_it'
    • None / ''    → 'ristosushi_it'   (fallback)
    • altrimenti   → lo stesso nome (es. 'pizza', 'messicano')
    """
    if not project or project.lower() == "sushi":
        return "ristosushi_it"
    return project.lower()

def set_current_db(project: str | None):
    """Va chiamata all’inizio di ogni request."""
    _current_db.set(map_project_to_db(project))

def get_current_db() -> str:
    """Da usare ovunque serva conoscere il DB corrente."""
    return _current_db.get()
