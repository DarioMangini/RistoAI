# menu_services/ingredient_similarity.py
"""
    file non utilizzato al momento
"""

from __future__ import annotations
import logging, threading
from typing import List
from sklearn.metrics.pairwise import cosine_similarity
from menu_services.vector_db import list_unique_ingredients
from core.vector_client import get_embedding

# Cache globale: lista ingredienti e relativi embedding
_raw_ing: list[str] = []
_raw_emb: list[list[float]] = []

# Flag che indica se il preload è stato completato (thread-safe)
_ready = threading.Event()         


def _loader():
    """
    Carica tutti gli ingredienti dal DB e ne calcola gli embedding.
    Operazione eseguita in background all'avvio.
    """
    global _raw_ing, _raw_emb
    logging.debug("[ingredient_similarity] start preload …")
    try:
        _raw_ing = list_unique_ingredients()
        _raw_emb = [get_embedding(i) for i in _raw_ing]
        logging.debug("[ingredient_similarity] %d ingredienti caricati", len(_raw_ing))
    finally:
        _ready.set()                
    logging.debug("[ingredient_similarity] preload done")


def bootstrap_async():
    """
    Lanciato una sola volta all’avvio dell’app (non blocca).
    """
    if not _ready.is_set():
        threading.Thread(target=_loader, daemon=True).start()


def get_similar(ing: str, top_n: int = 3) -> List[str]:
    """
    Restituisce i top-N ingredienti più simili.  
    Se il preload non è ancora finito ⇒ attende al massimo 3 s
    (nel peggiore dei casi tornerà lista vuota).
    """
    _ready.wait(timeout=3)          # attesa max 3 s
    if not _raw_emb:
        logging.warning("ingredient_similarity non disponibile (init non completato)")
        return []

    emb   = get_embedding(ing)
    sims  = cosine_similarity([emb], _raw_emb)[0]
    top   = sorted(zip(_raw_ing, sims), key=lambda x: x[1], reverse=True)[:top_n]
    return [w for w, _ in top]
