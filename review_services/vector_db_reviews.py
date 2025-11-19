# review_services/vector_db_reviews.py
"""
Modulo per eseguire ricerche semantiche nella tabella `recensioni`.

Usa lo stesso sistema di vettori SBERT del resto dell’app, 
ma include anche un peso sul voto (per favorire recensioni positive).
"""
from __future__ import annotations
import logging
from typing import List, Dict, Any
from core.vector_table import search_table
from psycopg2.errors import UndefinedTable

# Scoring personalizzato: 70% similarità + 30% voto (scala 1–5)
_EXTRA_SCORE = "(voto / 5.0) * 0.3"

# ───────────────────────────────────────────────────────────────────
def search_reviews(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Cerca le recensioni più rilevanti dato un input testuale.
    
    Args:
        query: testo descrittivo (es. "tonno fresco croccante")
        k: numero massimo di risultati

    Returns:
        Lista di dict con recensioni: id, voto, testo, piatti
    """
    try:
        return search_table(
            query = query,
            table = "recensioni",
            fields= "id,voto,recensione,piatti",
            k     = k,
            extra_score_sql = _EXTRA_SCORE
        )
    except UndefinedTable:
        logging.warning("Tabella recensioni assente; ritorno lista vuota")
        return []

logging.debug("[reviews_db] ready – reuses shared pool & SBERT")
