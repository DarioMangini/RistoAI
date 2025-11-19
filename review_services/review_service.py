# review_services/review_service.py
"""
Modulo di orchestrazione per le recensioni:
- Riceve le query generate dal modello LLM
- Esegue ricerche semantiche su ogni query
- Restituisce una lista `reviews_items` compatibile con i prompt loop dell'AI
"""

from __future__ import annotations
import logging, json
from typing import List, Dict, Any
from review_services.vector_db_reviews import search_reviews

# ────────────────────────────────────────────────────────────────
def fetch_reviews(review_queries: List[Dict[str, Any]],
                  top_k_per_query: int = 4) -> List[Dict[str, str]]:
    """
    Esegue più ricerche semantiche sulle recensioni in base alle query estratte
    dal modello LLM, e restituisce una lista pronta da inserire nel prompt.

    Args:
        review_queries: lista di dict con campi 'dish', 'keywords', 'intent'
        top_k_per_query: massimo numero di risultati per query

    Returns:
        Lista di dict del tipo:
        {"voto": "4", "snippet": "<testo intero recensione>", "dish": "Portofino"}
    """
    items: List[Dict[str, str]] = []

    for q in review_queries:
        dish   = (q.get("dish") or "").title()
        kw     = " ".join(q.get("keywords", []))
        intent = q.get("intent", "")

        query_text = " ".join([dish, kw]).strip() or dish or kw
        if not query_text:
            logging.debug("[review_service] query vuota – skip")
            continue

        rows = search_reviews(query_text, k=top_k_per_query)

        # Log semplificato per debug
        logging.debug(
            "[review_service] reviews per '%s' ➜ %s",
            query_text,
            json.dumps([
                {
                    "id": str(r["id"]),
                    "voto": r["voto"],
                    "snippet": r["recensione"]  
                } for r in rows
            ], ensure_ascii=False)
        )

        for r in rows:
            items.append({
                "dish": dish or ", ".join(eval(r.get("piatti", "[]"))),
                "voto": str(r["voto"]),
                "snippet": r["recensione"]
            })

    logging.debug("[review_service] produced %d review-items", len(items))
    return items
