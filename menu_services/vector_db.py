# menu_services/vector_db.py
"""
Funzioni di dominio per operare sulla tabella `menu` nel database.
────────────────────────────────────────────────────────────────────
• search_menu(query, k):           restituisce i k piatti più simili a un testo
• list_menu(dish_type=None):       restituisce tutto il menu o solo piatti di un tipo
• list_unique_ingredients():       restituisce una lista di tutti gli ingredienti unici
"""

from __future__ import annotations
from typing import List, Dict, Any
from core.vector_table  import search_table     # Funzione di similarità semantica
from core.vector_client import _run             # Funzione per eseguire query SQL (con pool condiviso)

# ───────────────────────────────────────────────────────────────────
def search_menu(query: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Ricerca semantica nel menu usando similarità vettoriale.
    Restituisce i `k` piatti più simili al testo `query`.

    Args:
        query: testo di input dell'utente (es. "qualcosa col salmone")
        k: numero massimo di risultati

    Returns:
        Lista di dizionari con i piatti più rilevanti
    """
    return search_table(
        query           = query,
        table           = "menu",
        fields          = "id,name,type,ingredients,description,price",
        k               = k,
        extra_score_sql = ""          # solo similarità
    )

# ───────────────────────────────────────────────────────────────────
def list_menu(dish_type: str | None = None) -> List[Dict[str, Any]]:
    """
    Estrae tutti i piatti dal database, eventualmente filtrando per tipo.

    Args:
        dish_type: categoria (es. "uramaki", "ceviche", "dolci", ...)

    Returns:
        Lista ordinata di piatti come dizionari
    """
    sql  = "SELECT id,name,type,ingredients,description,price FROM menu"
    args = []
    if dish_type:
        sql += " WHERE LOWER(type)=LOWER(%s)"
        args.append(dish_type)
    sql += " ORDER BY id"
    return _run(sql, args, dict_cursor=True)

# ───────────────────────────────────────────────────────────────────
def list_unique_ingredients() -> List[str]:
    """
    Estrae tutti gli ingredienti unici presenti nella colonna `ingredients` della tabella `menu`.

    Returns:
        Lista di stringhe (ingredienti unici ordinati alfabeticamente)
    """
    sql = """
        SELECT ing
        FROM (
            SELECT DISTINCT UNNEST(ingredients) AS ing
            FROM menu
            WHERE ingredients IS NOT NULL
        ) sub
        ORDER  BY LOWER(ing);
    """
    rows = _run(sql)
    return [r[0] for r in rows]

