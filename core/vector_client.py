# core/vector_client.py
"""
Gestisce:
• Connessione al database PostgreSQL (con pool condiviso)
• Encoding vettoriale via microservizio HTTP (no SentenceTransformer in RAM)
"""

from __future__ import annotations
import logging, os, math, functools, json
import psycopg2, psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
import requests
from typing import List, Any
from core.config import Config
from core.db_router import get_current_db
from psycopg2.sql import Composed
import os, logging
import math
from typing import List, Any
from sentence_transformers  import SentenceTransformer
import openai

# ------------- Pool PostgreSQL (uno per DB) -------------
_POOLS: dict[str, SimpleConnectionPool] = {}
_PG_STATIC = {
    "user":     Config.DB_USER,
    "password": Config.DB_PASS,
    "host":     Config.DB_HOST,
    "port":     Config.DB_PORT,
}

# Configurazione
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local_cpu") # local_cpu | openai
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Carica il modello in memoria solo se necessario (singleton)
_LOCAL_MODEL = None

def _get_local_model():
    global _LOCAL_MODEL
    if _LOCAL_MODEL is None:
        logging.info("Caricamento modello embedding locale (CPU)...")
        # Usa un modello molto leggero ma efficace
        _LOCAL_MODEL = SentenceTransformer("all-MiniLM-L6-v2") 
    return _LOCAL_MODEL

def get_pool() -> SimpleConnectionPool:
    dbname = get_current_db()
    if dbname not in _POOLS:
        _POOLS[dbname] = SimpleConnectionPool(5, 40, dbname=dbname, **_PG_STATIC)
        logging.debug("[vector_client] PG pool ready for %s", dbname)
    return _POOLS[dbname]

def _run(sql: str | Composed, args: Any = None, dict_cursor: bool = False) -> list[Any]:
    pool = get_pool()
    conn = pool.getconn()
    try:
        factory = psycopg2.extras.RealDictCursor if dict_cursor else None
        with conn.cursor(cursor_factory=factory) as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        pool.putconn(conn)

# ───────── HTTP embedding client ─────────
# Usa all-mpnet-base-v2 (768d) di default
EMB_URL = os.getenv("EMB_URL_MPNET", "http://localhost:5020/embedding/all-mpnet-base-v2")
_HTTP = requests.Session()

def _parse_vec(resp_json):
    """
    Prova varie forme comuni:
    - {"embedding":[...]}  | {"vector":[...]} | {"data":[...]} | [...]
    """
    if isinstance(resp_json, list):
        return resp_json
    if isinstance(resp_json, dict):
        for k in ("embedding", "vector", "data"):
            if k in resp_json and isinstance(resp_json[k], list):
                return resp_json[k]
    # last resort: alcuni servizi incapsulano in {"result":{"embedding":[...]}}
    if isinstance(resp_json, dict) and "result" in resp_json:
        r = resp_json["result"]
        if isinstance(r, dict):
            for k in ("embedding", "vector", "data"):
                if k in r and isinstance(r[k], list):
                    return r[k]
    return None

@functools.lru_cache(maxsize=4096)
def _embed_one_cached(text: str) -> tuple[float, ...]:
    payload = {"text": text or ""}
    try:
        r = _HTTP.post(EMB_URL, json=payload, timeout=5)
        r.raise_for_status()
        vec = _parse_vec(r.json())
        if not isinstance(vec, list):
            raise ValueError("Embedding non trovato nel JSON")
        # normalizza lato client per sicurezza
        s = sum(x*x for x in vec)
        norm = math.sqrt(s) or 1.0
        return tuple(x / norm for x in vec)
    except Exception as e:
        logging.error("[vector_client] embed error: %s | url=%s | payload=%s",
                      e, EMB_URL, json.dumps(payload, ensure_ascii=False))
        return tuple()  # evita crash: il chiamante potrà gestire embedding vuoto

def get_embedding(text: str) -> List[float]:
    text = text.replace("\n", " ")
    
    if EMBEDDING_PROVIDER == "openai":
        # Uso OpenAI (richiede API Key)
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY mancante")
        client = openai.Client(api_key=OPENAI_API_KEY)
        resp = client.embeddings.create(input=[text], model="text-embedding-3-small")
        return resp.data[0].embedding
        
    else:
        # Uso CPU Locale (Gratis, funziona su ogni PC)
        model = _get_local_model()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()
