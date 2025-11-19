# chat_services/order_builder.py
"""
Converte la lista di criteri (prodotti + delivery) in JSON ordine
pronto per il frontend. Aggiunge prodotti simili a ogni richiesta.
"""
from __future__ import annotations
import json, logging
from typing import List, Dict, Any
from menu_services.vector_db import search_menu
from core.aliases import resolve as resolve_alias

def _normalize_name(name: str) -> str:
    return (name or "").strip().lower()


def _rows_from_cache(prod_name: str,
                     menu_cache: dict[str, List[Dict[str, Any]]] | None) -> List[Dict[str, Any]] | None:
    if not menu_cache:
        return None

    key = _normalize_name(prod_name)
    if key in menu_cache:
        return menu_cache[key]

    alias_key = _normalize_name(resolve_alias(prod_name))
    if alias_key != key and alias_key in menu_cache:
        return menu_cache[alias_key]
    return None


def _similar_products(prod_name: str,
                      max_k: int = 3,
                      menu_cache: dict[str, List[Dict[str, Any]]] | None = None) -> List[Dict[str,Any]]:
    """
    Restituisce fino a `max_k` piatti simili al nome dato,
    inclusi nome, ingredienti, prezzo e un punteggio interno.
    """
    rows = _rows_from_cache(prod_name, menu_cache)
    if rows is None:
        rows = search_menu(prod_name, k=max_k)
    rows = list(rows[:max_k])

    return [{
        "name": r["name"],
        "ingredients": r.get("ingredients", []),
        "price": float(r.get("price") or 0),
        "score": idx            # proxy score
    } for idx, r in enumerate(rows)]

# funzione non usata, messa come wrapper per una futura implementazione di allergie, aggiunte, esclusioni ecc..
def _enrich_prod(prod: Dict[str,Any]) -> Dict[str,Any]:
    """
    Versione semplificata: restituisce il prodotto originale così com’è.
    """
    return prod

# ------------------------------------------------------------------ #
def build_order(criteria_list: List[Dict[str,Any]],
                menu_cache: dict[str, List[Dict[str, Any]]] | None = None
                ) -> tuple[list, str]:
    """
    Converte la lista dei criteri in JSON ordine per il frontend/chatbot.

    Returns:
        - Lista nativa (dict)
        - Stringa JSON (indentata)
    """
    order_all: List[Dict[str,Any]] = []

    for crit in criteria_list:
        entry = {
            "delivery_type": crit.get("delivery_type",""),
            "delivery_day":  crit.get("delivery_day",""),
            "delivery_hour": crit.get("delivery_hour",""),
            "address":       crit.get("address",""),
            "products":      []
        }

        for prod in crit.get("confirmed_products", []):
            # alias resolution
            prod["name"] = resolve_alias(prod.get("name",""))
            # similar products (riusa cache quando disponibile)
            similars = _similar_products(prod["name"], menu_cache=menu_cache)
            entry["products"].append({
                "original_product": _enrich_prod(prod),
                "similar_products": similars
            })
        order_all.append(entry)

    return order_all, json.dumps(order_all, indent=2)
