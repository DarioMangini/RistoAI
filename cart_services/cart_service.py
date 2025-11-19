# cart_services/cart_service.py
"""
Servizi per la gestione del carrello su PostgreSQL (tabella `cart_data`).

Funzioni esposte:
──────────────────────────────────────────────────────
• fetch_cart(sessionid)       → restituisce l'ultimo carrello salvato per una sessione
• upsert_cart(payload_json)   → crea o aggiorna un carrello, in base alla sessione
"""
from __future__ import annotations
import json, logging, threading
from datetime import datetime
from core.vector_client import get_pool


_TABLE_LOCK = threading.Lock()
_TABLE_READY = False


def _ensure_table_once():
    """
    Esegue le CREATE TABLE una sola volta riutilizzando il connection pool.
    """
    global _TABLE_READY
    if _TABLE_READY:
        return

    with _TABLE_LOCK:
        if _TABLE_READY:
            return
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS cart_data (
                            id          SERIAL PRIMARY KEY,
                            sessionid   TEXT NOT NULL,
                            action_type TEXT NOT NULL,
                            cart_items  TEXT NOT NULL,
                            total       REAL NOT NULL,
                            product     TEXT,
                            timestamp   TEXT NOT NULL
                        );
                    """)
                    cur.execute("""
                        CREATE INDEX IF NOT EXISTS idx_cart_data_sessionid
                        ON cart_data(sessionid);
                    """)
            _TABLE_READY = True
        finally:
            pool.putconn(conn)

# ──────────────────────────────────────────────────────────────────────
def fetch_cart(sessionid: str) -> dict:
    """
    Recupera l'ultima versione del carrello per una sessione specifica.

    Args:
        sessionid: identificatore univoco della sessione utente

    Returns:
        Dizionario JSON già pronto per essere restituito all'API,
        con eventuale messaggio di errore o carrello trovato.
    """
    logging.debug("[cart_service] fetch_cart sessionid=%s", sessionid)

    _ensure_table_once()

    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, action_type, cart_items, total, product, timestamp
                FROM   cart_data
                WHERE  sessionid = %s
                ORDER  BY id DESC
                LIMIT  1;
            """, (sessionid,))

            row = cur.fetchone()
            if not row:
                return {
                    "status": "not_found",
                    "message": "No cart data found for this session",
                    "cart": [],
                    "total": "0.00",
                }

        (record_id, action_type, cart_items_json,
         total, product_json, ts) = row

        # Decodifica sicura del campo cart_items
        try:
            cart_items = json.loads(cart_items_json or "[]")
        except json.JSONDecodeError:
            logging.error("[cart_service] cart_items JSON malformato")
            cart_items = []

        # Decodifica sicura del campo product (può essere None)
        try:
            product = json.loads(product_json) if product_json else None
        except json.JSONDecodeError:
            logging.error("[cart_service] product JSON malformato")
            product = None

        logging.debug("[cart_service] fetch_cart OK id=%s", record_id)
        return {
            "status": "success",
            "record_id": record_id,
            "action_type": action_type,
            "cart": cart_items,
            "total": str(total),
            "last_product": product,
            "timestamp": ts,
        }
    finally:
        pool.putconn(conn)

# ──────────────────────────────────────────────────────────────────────
def upsert_cart(data: dict) -> dict:
    """
    Inserisce o aggiorna il carrello di una sessione.

    Richiede i seguenti campi nel payload:
    - type: tipo di azione (es. "add", "remove", "update")
    - cart: lista di prodotti
    - total: totale del carrello
    - sessionid (o sessionId): identificatore della sessione

    Returns:
        Dizionario con esito dell’operazione e record_id
    """
    logging.debug("[cart_service] upsert_cart payload=%s", data)

    # Verifica la presenza dei campi obbligatori
    required = {"type", "cart", "total"}
    if missing := required - data.keys():
        return {"error": f"Missing required fields: {', '.join(missing)}"}

    # Supporta sessionid in due possibili formati
    sessionid   = data.get("sessionid") or data.get("sessionId")
    if not sessionid:
        return {"error": "Session ID not provided"}

    action_type = data["type"]                # add | remove | update
    cart_items  = data["cart"]
    total       = data["total"]
    product     = data.get("product")

    # Timestamp corrente formattato
    timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Serializzazione in JSON per salvataggio nel DB
    cart_json = json.dumps(cart_items or [])
    product_json = json.dumps(product) if product else None

    _ensure_table_once()

    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Verifica se esiste già un record per la sessione
                cur.execute("SELECT id FROM cart_data WHERE sessionid = %s;", (sessionid,))
                row = cur.fetchone()

                if row:
                    # Update se già esiste
                    cur.execute("""
                        UPDATE cart_data
                           SET action_type = %s,
                               cart_items  = %s,
                               total       = %s,
                               product     = %s,
                               timestamp   = %s
                         WHERE sessionid   = %s
                     RETURNING id;
                    """, (action_type, cart_json, total, product_json,
                          timestamp, sessionid))
                    record_id = cur.fetchone()[0]
                    op = "updated"
                else:
                    # Insert se non esiste ancora
                    cur.execute("""
                        INSERT INTO cart_data
                            (sessionid, action_type, cart_items, total, product, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s)
                     RETURNING id;
                    """, (sessionid, action_type, cart_json, total,
                          product_json, timestamp))
                    record_id = cur.fetchone()[0]
                    op = "created"

        logging.debug("[cart_service] cart %s id=%s", op, record_id)
        return {
            "status":  "success",
            "message": "Cart data synchronized successfully",
            "record_id": record_id,
        }
    finally:
        pool.putconn(conn)
