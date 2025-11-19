# menu_services/search_service.py
"""
Wrapper attorno a `vector_db.search_menu()`.
Include:
• Ricerca semantica principale (demandata a vector_db, che usa pgvector)
• Fallback leggero (token overlap + difflib), senza modelli locali
"""

import logging, difflib, threading, time
from typing import List, Dict, Any
from menu_services.vector_db import list_menu

_MENU_CACHE_TTL = 300.0  # seconds
_MENU_CACHE_LOCK = threading.Lock()
_MENU_CACHE: dict[str, Any] = {"items": [], "ts": 0.0}


def _get_menu_snapshot() -> List[Dict[str, Any]]:
    """
    Restituisce una copia cache del menu completo (refreshed ogni TTL).
    """
    now = time.time()
    if now - _MENU_CACHE["ts"] > _MENU_CACHE_TTL or not _MENU_CACHE["items"]:
        with _MENU_CACHE_LOCK:
            if now - _MENU_CACHE["ts"] > _MENU_CACHE_TTL or not _MENU_CACHE["items"]:
                items = list_menu()
                _MENU_CACHE["items"] = items
                _MENU_CACHE["ts"] = time.time()
                logging.debug("[search_service] refreshed menu cache (%d items)", len(items))
    return _MENU_CACHE["items"]


def invalidate_menu_cache():
    with _MENU_CACHE_LOCK:
        _MENU_CACHE["items"] = []
        _MENU_CACHE["ts"] = 0.0

def _token_overlap_score(a: str, b: str) -> float:
    """
    Heuristica: richiede almeno 1 token in comune.
    Punteggio = ratio(difflib) + 0.1 * |overlap|.
    """
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a or not b:
        return 0.0
    at = set(a.split())
    bt = set(b.split())
    overlap = len(at & bt)
    if overlap == 0:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return ratio + 0.1 * overlap

def best_menu_match(request_name: str) -> Dict[str, Any] | None:
    """
    Restituisce il piatto più simile con euristica leggera
    (usata solo come Fallback se la ricerca vettoriale non ha dato risultati).
    """
    logging.debug("[search_service] best_menu_match for %s", request_name)
    name = (request_name or "").strip()
    if not name:
        return None

    candidates = _get_menu_snapshot()
    best = None
    best_sc = 0.0

    for row in candidates:
        cand = (row.get("name") or "").strip()
        if not cand:
            continue
        sc = _token_overlap_score(name, cand)
        if sc > best_sc:
            best_sc = sc
            best = row

    return best
