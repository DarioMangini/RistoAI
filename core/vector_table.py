# core/vector_table.py
"""
Esegue una ricerca semantica su una tabella PostgreSQL con colonna pgvector.

Funzione generica:
• search_table(query, table, fields, k, extra_score_sql)
"""

from __future__ import annotations
from typing import List, Dict, Any
from core.vector_client import get_embedding, _run
import logging

def search_table(query: str, *,
                 table: str,
                 fields: str = "*",
                 k: int = 5,
                 extra_score_sql: str = "") -> List[Dict[str, Any]]:
    """
    Cerca nei dati una corrispondenza semantica basata su embedding SBERT.
    Il punteggio può includere un fattore extra (es. voto, popolarità…).

    Args:
        query: stringa di ricerca testuale
        table: nome della tabella da interrogare
        fields: colonne da restituire
        k: numero massimo di risultati
        extra_score_sql: opzionale, per personalizzare lo score finale

    Returns:
        Lista di risultati ordinati per rilevanza (score)
    """
    emb = get_embedding(query)
    emb_literal = f"ARRAY{emb}::vector"

    sim_sql = f"(1 - (embedding <=> {emb_literal}))"
    order_sql = f"{sim_sql}" if not extra_score_sql \
                else f"({sim_sql} + {extra_score_sql})"

    sql = f"""
        SELECT {fields},
               {sim_sql}   AS cos_sim,
               {order_sql} AS score
        FROM   {table}
        ORDER  BY score DESC
        LIMIT  %s;
    """
    logging.debug("[vector_table] search %s '%s' k=%d", table, query, k)
    return _run(sql, (k,), dict_cursor=True)
