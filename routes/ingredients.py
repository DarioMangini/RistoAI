# routes/ingredients.py
from flask import Blueprint, jsonify, request
from menu_services.vector_db import list_unique_ingredients # Recupera tutti gli ingredienti unici presenti nel menu
import unicodedata, re, logging
from core.db_router import set_current_db


# Definizione del Blueprint per il modulo ingredienti
ingredients_bp = Blueprint("ingredients_bp", __name__)

def _normalize_id(name: str) -> str:
    """
    Normalizza un nome in un ID leggibile e privo di simboli, adatto a URL o frontend.
    Esempio: "Salsa di Soia" → "salsadisoia"
    """
    txt = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]", "", txt).lower()

def _safe_entries() -> list[dict]:
    """
    Elabora la lista di ingredienti:
    - rimuove valori nulli o vuoti
    - restituisce una lista ordinata con campo `id` normalizzato e `nome` originale
    """
    raw = list_unique_ingredients()              
    clean = [r for r in raw if r]                
    data = [{"id": _normalize_id(n), "nome": n} for n in clean]
    return sorted(data, key=lambda x: x["nome"].lower())


@ingredients_bp.route("/ingredienti", methods=["GET"])
@ingredients_bp.route("/ingredients",   methods=["GET"])  # alias
def ingredients():
    project = request.args.get("project") or request.headers.get("X-Project")
    set_current_db(project)                               # <— NEW

    try:
        return jsonify({"ingredienti": _safe_entries()}), 200
    except Exception as exc:
        logging.exception("Errore nella route /ingredienti")
        return jsonify({"error": str(exc)}), 500
