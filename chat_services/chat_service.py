# chat_services/chat_service.py
"""
Entry-point principale della chat AI.
Costruisce il prompt personalizzato a partire dalla cronologia,
recupera criteri e recensioni via LLM, arricchisce con menu/cart/reviews,
e interroga il modello vLLM per generare la risposta.
"""

import json, logging, os, re, time
from wsgiref import headers
import redis
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import requests
from menu_services import vector_db
from review_services.review_query_api import extract_review_queries
from review_services.review_service    import fetch_reviews
from menu_services.search_service import best_menu_match
from chat_services.order_builder import build_order
from core.aliases import resolve as resolve_alias
from core.prompt_utils import (fill_prompt_loop,
                                   process_conditional_blocks,
                                   fix_italian_encoding)
from chat_services.criteria_api import extract_criteria
from cart_services.cart_service import fetch_cart
from core.db_router import set_current_db 
from core.prompt_store import get_prompt
from datetime import datetime
from concurrent.futures import as_completed
from pathlib import Path

from core.llm_formatting import format_messages_for_vllm

# Configurazione modello LLM
LLM_URL   = os.getenv("LLM_URL", "http://localhost:8000/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "google/gemma-3-27b-it")
DEFAULT_PROMPT_FILE = Path(
    os.getenv(
        "CHAT_PROMPT_FILE",
        Path(__file__).resolve().parents[1] / "prompts" / "demo-chat.txt"
    )
)

# ────────────────────────────────────────────────────────────────
# Thread pool condiviso per task asincroni (criteri + recensioni)
EXECUTOR = ThreadPoolExecutor(max_workers=32)

# Redis per mantenere lo stato della conversazione (es. preferenze di consegna)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
REDIS_TTL = 7200        # 2 h in secondi

# TTL-cache “interno” per fetch_reviews è già gestito dal modulo

def _with_db(project, fn, *args, **kwargs):
    """
    Wrapper che imposta il DB corretto *dentro* il thread
    e poi invoca la funzione reale.
    """
    def inner():
        set_current_db(project)
        return fn(*args, **kwargs)
    return inner

def _as_text(x): 
    return x if isinstance(x, str) else ""

# ------------------------------------------------------------------ #
def _normalize_name(name: str) -> str:
    return (name or "").strip().lower()


def _gather_menu_queries(criteria: List[Dict[str, Any]]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for crit in criteria:
        for prod in crit.get("confirmed_products", []):
            raw = (prod.get("name") or "").strip()
            if not raw:
                continue
            raw_key = _normalize_name(raw)
            mapping.setdefault(raw, set()).add(raw_key)

            canonical = resolve_alias(raw)
            canon_key = _normalize_name(canonical)
            if canon_key != raw_key:
                mapping.setdefault(canonical, set()).add(canon_key)
    return mapping


def _prefetch_menu_data(criteria: List[Dict[str, Any]],
                        project: str) -> dict[str, List[Dict[str, Any]]]:
    queries = _gather_menu_queries(criteria)
    if not queries:
        return {}

    futures = {}
    for query, keys in queries.items():
        futures[EXECUTOR.submit(
            _with_db(project, vector_db.search_menu, query, 3)
        )] = (query, keys)

    menu_cache: dict[str, List[Dict[str, Any]]] = {}
    for fut in as_completed(futures):
        query, keys = futures[fut]
        try:
            rows = fut.result()
        except Exception as exc:
            logging.warning("[chat_service] prefetch menu error for '%s': %s", query, exc)
            rows = []

        if not rows:
            fallback = best_menu_match(query)
            rows = [fallback] if fallback else []

        for key in keys:
            menu_cache[key] = rows

    logging.debug("[chat_service] prefetched %d menu keys", len(menu_cache))
    return menu_cache


def _lookup_menu_rows(prod_name: str,
                      menu_cache: dict[str, List[Dict[str, Any]]] | None) -> List[Dict[str, Any]]:
    if not prod_name:
        return []

    key = _normalize_name(prod_name)
    if menu_cache is not None:
        if key in menu_cache:
            return menu_cache[key]
        alias_key = _normalize_name(resolve_alias(prod_name))
        if alias_key in menu_cache:
            return menu_cache[alias_key]

    # Fallback a chiamata singola se non era stato prefetcheato
    rows = vector_db.search_menu(prod_name, k=3)
    if not rows:
        fallback = best_menu_match(prod_name)
        rows = [fallback] if fallback else []

    if menu_cache is not None:
        menu_cache[key] = rows

    return rows


def build_menu_items(criteria: List[Dict[str,Any]],
                     max_items: int = 8,
                     menu_cache: dict[str, List[Dict[str, Any]]] | None = None
                     ) -> List[Dict[str,str]]:
    """
    Costruisce la lista di piatti confermati per il prompt,
    cercandoli nel DB (search_menu o fuzzy match).

    Returns:
        Lista di dict con campi name, type, description, ingredients, price
    """
    items: List[Dict[str,str]] = []
    for crit in criteria:
        for prod in crit.get("confirmed_products", []):
            if len(items) >= max_items:
                break
            rows = _lookup_menu_rows(prod.get("name",""), menu_cache)
            if rows:
                row = rows[0]
                items.append({
                    "name": row["name"].title(),
                    "type": (row.get("type") or "").title(),
                    "description": row.get("description",""),
                    "ingredients": ", ".join(row.get("ingredients") or []),
                    "price": f'{row.get("price",0):.2f}'
                })
    return items
    

# ────────────────────────────────────────────────────────────────
# Gestione memoria conversazionale su Redis
def _redis_key(sid: str) -> str:
    return f"convo:{sid}"

def _get_state(sid: str) -> dict:
    """Restituisce lo stato (hash) o dict vuoto."""
    return REDIS.hgetall(_redis_key(sid)) or {}

def _save_state(sid: str, patch: dict):
    """Aggiorna i campi e rinnova la TTL."""
    if patch:
        REDIS.hset(_redis_key(sid), mapping=patch)
    REDIS.expire(_redis_key(sid), REDIS_TTL)

# ------------------------------------------------------------------ #
def chat(payload: Dict[str,Any]) -> Dict[str,Any]:
    """
    Entry-point invocato da /chat (routes.chat).
    Riceve cronologia + prompt + sessione e restituisce la risposta AI + ordine.
    """
    # Estrazione campi di input
    prompts      = payload.get("prompts", "")
    conv_history = payload.get("conversation_history", [])
    sessionid    = payload.get("sessionid", "")
    temperature  = payload.get("temperature", 0.7)
    top_p        = payload.get("top_p", 0.9)
    top_k        = payload.get("top_k", 50)
    replyformat  = payload.get("replyformat", "")
    project      = payload.get("project", "")

    prompts = get_prompt(project)
    if not prompts:
        prompts      = payload.get("prompts", "")
    if not prompts:
        try:
            prompts = DEFAULT_PROMPT_FILE.read_text(encoding="utf-8")
            logging.info("[chat_service] prompt caricato da %s", DEFAULT_PROMPT_FILE)
        except FileNotFoundError:
            logging.error("[chat_service] Prompt file mancante (%s)", DEFAULT_PROMPT_FILE)

    if not prompts or conv_history is None:
        return {"error": "Missing prompts or conversation_history"}

    if project:
        logging.debug("[DEBUG chat_service] ECCO IL PROGETTO: %s", project)

    # Normalizzazione della cronologia conversazionale
    if isinstance(conv_history, dict):
        conv_list = [
            conv_history[k] for k in sorted(
                conv_history.keys(),
                key   = lambda x: int(x) if str(x).isdigit() else x,
                reverse = True                     # 2 → 1 → 0
            )
        ]
        logging.debug("[chat_service] conv_list (dict) ordinata ➜ %s",
                      json.dumps(conv_list, indent=2, ensure_ascii=False))

    elif isinstance(conv_history, list):
        conv_list = conv_history
    else:
        conv_list = []

    if not conv_list:
        return {"error": "Empty conversation_history after normalisation"}
    # ────────────────────────────────────────────────────────────────

    # Recupero carrello e stato precedente  
    cart_resp   = fetch_cart(sessionid)
    cart_items  = cart_resp.get("cart", [])
    cart_total  = cart_resp.get("total", "0.00")

    # --- conversation memory ----------------------------------------
    conv_state  = _get_state(sessionid)          # può essere {}
    logging.debug("[chat_service] redis state ➜ %s", conv_state)

    # Estrazione ultimo messaggio utente
    last_user_msg = ""
    for msg in reversed(conv_list):
        if isinstance(msg, dict) and msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # Avvia in parallelo estrazione criteri e review queries (→ 2 API LLM)
    t_llm = time.perf_counter()
    fut_criteria = EXECUTOR.submit(
        _with_db(project, extract_criteria,
                 [{"role": "user", "content": last_user_msg}], sessionid)
    )
    fut_revq = EXECUTOR.submit(
        _with_db(project, extract_review_queries,
                 [{"role": "user", "content": last_user_msg}], sessionid)
    )

    # Aspetta entrambi
    criteria_list, review_q = None, None
    for fut in as_completed([fut_criteria, fut_revq]):
        ms = (time.perf_counter() - t_llm) * 1000
        if fut is fut_criteria:
            criteria_list = fut.result()
            logging.debug("[chat_service] criteria_api ✓  %.0f ms", ms)
        else:
            review_q = fut.result()
            logging.debug("[chat_service] review_query_api ✓  %.0f ms", ms)

    criteria_list = criteria_list or []
    review_q      = review_q      or {"needs_reviews": False}

    # Aggiorna stato di sessione (es. indirizzo, orario, delivery_type)
    latest = criteria_list[0] if criteria_list else {}
    merged = conv_state.copy()

    SENTINEL = {"No data", "no data", "n/a", "-", ""}

    for fld in ["delivery_type", "delivery_day",
                "delivery_hour", "address"]:
        raw = (latest.get(fld) or "").strip()
        if raw.lower() not in SENTINEL:
            merged[fld] = raw                    # solo se “valido”

    # salva dopo il filtro
    _save_state(sessionid, merged)


    logging.debug("[chat_service] criteria_list (%d items) ➜ %s",
                  len(criteria_list),
                  json.dumps(criteria_list[:2], indent=2, ensure_ascii=False))
    logging.debug("[chat_service] review_q ➜ %s",
                  json.dumps(review_q, indent=2, ensure_ascii=False))

    # Menu dinamico e recensioni asincrone
    menu_cache = _prefetch_menu_data(criteria_list, project or "")
    menu_items = build_menu_items(criteria_list, menu_cache=menu_cache)
    logging.debug("[chat_service] menu_items %d", len(menu_items))
    fut_reviews = None
    if review_q.get("needs_reviews"):
        # ⚠️  passa il DB corretto al thread di fetch_reviews
        fut_reviews = EXECUTOR.submit(
            _with_db(project, fetch_reviews, review_q.get("review_queries", []))
        )

    # Costruzione dell’ordine
    order_list, order_json = build_order(criteria_list, menu_cache=menu_cache)

    logging.debug("[chat_service] order_list (%d criteria)", len(order_list))

    # Preparazione del system prompt completo
    reviews_items = fut_reviews.result() if fut_reviews else []
    logging.debug("[chat_service] reviews_items %d", len(reviews_items))

    sys_prompt = prompts
    logging.debug("[chat_service] menu_items      ➜ %s", json.dumps(menu_items, indent=2, ensure_ascii=False))
    sys_prompt = fill_prompt_loop(sys_prompt, menu_items,  "menu")
    logging.debug("[chat_service] cart_items      ➜ %s", json.dumps(cart_items, indent=2, ensure_ascii=False))
    sys_prompt = fill_prompt_loop(sys_prompt, cart_items,  "products_cart")
    logging.debug("[chat_service] reviews_items   ➜ %s", json.dumps(reviews_items, indent=2, ensure_ascii=False))
    sys_prompt = fill_prompt_loop(sys_prompt, reviews_items, "reviews")
    logging.debug("[chat_service] delivery_state  ➜ %s", merged)

    sys_prompt = process_conditional_blocks(
        sys_prompt,
        {
            "menu":     "1" if menu_items else "",
            "cart":     "1" if cart_items else "",
            "reviews":  "1" if reviews_items else "",
            "delivery": "1" if merged.get("delivery_type") else ""
        }
    )
    # placeholders delivery_*
    for fld in ["delivery_type", "delivery_day", "delivery_hour", "address"]:
        sys_prompt = sys_prompt.replace(f"{{{fld}}}", _as_text(merged.get(fld)))
        
    sys_prompt = sys_prompt.replace("{cart_total}", cart_total)
    logging.debug("[chat_service] system_prompt ready (%d chars)", len(sys_prompt))

    # ––––– DEBUG: prompt finale con tutti i placeholder risolti –––––
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        # mostra solo i primi 800 caratteri per non riempire i log
        preview = sys_prompt
        logging.debug("[chat_service] SYSTEM_PROMPT ➜\n%s", preview)

    # Costruzione messaggi finali da inviare a vLLM
    system_msg = {"role": "system", "content": sys_prompt}
    messages   = [system_msg] + conv_list          # <-- usa la lista normalizzata
    formatted_messages = format_messages_for_vllm(messages)


    # Chiamata al modello LLM
    payload_llm = {
        "model": LLM_MODEL,
        "messages": formatted_messages,
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "max_tokens": 8192
    }
    if replyformat:
        payload_llm["response_format"] = {
            "type":"json_object" if replyformat.lower()=="json" else "text"
        }

    logging.debug("[chat_service] chiamo vLLM…")
    try:
        headers = {}
        if "api.openai.com" in LLM_URL or os.getenv("LLM_API_KEY"):
            headers["Authorization"] = f"Bearer {os.getenv('LLM_API_KEY', '')}"
        r = requests.post(LLM_URL, json=payload_llm, headers=headers, timeout=180)
        r.raise_for_status()
        llm = r.json()
        content = llm["choices"][0]["message"]["content"]
    except Exception as exc:
        logging.error("[chat_service] errore LLM %s", exc)
        return {"error":"Model API error"}

    answer = fix_italian_encoding(content)

    # --- risposta finale -------------------------------------------
    return {
        "model": LLM_MODEL,
        "created_at": datetime.utcnow().isoformat(),
        "message": {"role":"assistant", "content": answer},
        "done": llm["choices"][0]["finish_reason"] == "stop",
        "order": order_json
    }
