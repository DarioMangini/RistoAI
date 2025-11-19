# routes/chat.py
from flask import Blueprint, request, jsonify
import logging
from chat_services import chat_service  # Funzione che gestisce la logica conversazionale
from core.db_router import set_current_db

chat_bp = Blueprint("chat_bp", __name__)

@chat_bp.route("/chat", methods=["POST"])
def chat_route():
    # 1. parsing del JSON (gestisci l’errore qui)
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    # 2. selezione DB dinamico
    set_current_db(payload.get("project"))

    logging.debug("[/chat] payload: %s", payload)

    # 3. logica conversazionale
    resp = chat_service.chat(payload)

    status = 200 if "error" not in resp else 500
    return jsonify(resp), status