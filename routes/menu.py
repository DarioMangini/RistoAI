# routes/menu.py
from flask import Blueprint, jsonify, request
from menu_services.vector_db import list_menu  # Funzione per recuperare i piatti dal menu (filtrati o meno)
from core.db_router import set_current_db

# Definizione del Blueprint per il modulo menu
menu_bp = Blueprint("menu_bp", __name__)


@menu_bp.route("/menu", methods=["GET"])
def menu():
    # ?project=pizza  oppure Header: X-Project: pizza (fallback default = sushi)
    project   = request.args.get("project") or request.headers.get("X-Project")
    set_current_db(project)                       # <— NEW

    dish_type = request.args.get("type")          # filtro facoltativo
    items     = list_menu(dish_type)

    # Decimal → float per JSON
    for it in items:
        if it["price"] is not None:
            it["price"] = float(it["price"])

    return jsonify({"menu": items}), 200

    return jsonify({"menu": items}), 200
