# routes/cart.py
from flask import Blueprint, request, jsonify
import logging
from cart_services.cart_service import fetch_cart, upsert_cart # Funzioni per gestire carrelli

cart_bp = Blueprint("cart_bp", __name__)

# ------------------------------------------------------------------- #
@cart_bp.route("/getcart", methods=["GET"])
def get_cart():
    """
    Recupera l'ultimo carrello salvato per una sessione specifica.
    Parametri:
    - sessionid (GET): ID della sessione da cui recuperare il carrello

    Output:
    - JSON con i dati del carrello o errore se non trovato
    """
    sessionid = request.args.get("sessionid")
    if not sessionid:
        return jsonify({"error": "Missing sessionid parameter"}), 400

    resp = fetch_cart(sessionid)
    status = 200 if resp.get("status") == "success" else 404
    return jsonify(resp), status

# ------------------------------------------------------------------- #
@cart_bp.route("/cart", methods=["POST"])
def sync_cart():
    """
    Salva o aggiorna un carrello per una sessione specifica.
    Richiede un payload JSON nel formato:
    {
        "type": "...",
        "cart": [...],
        "total": ...,
        "sessionid": "..."
    }
    
    Output:
    - JSON con conferma o errore
    """
    try:
        payload = request.get_json(force=True)
    except Exception as exc:
        logging.error("[sync_cart] bad JSON: %s", exc)
        return jsonify({"error": "Invalid JSON payload"}), 400

    result = upsert_cart(payload)

    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200
