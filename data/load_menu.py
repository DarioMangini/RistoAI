#!/usr/bin/env python3
"""
menu_sushi.py
───────────────────────────────────────────────────────────────────────────────
Carica il file `menu.json` nel database PostgreSQL (`tabella menu`), aggiungendo
per ogni piatto un **embedding semantico** SBERT (768 dimensioni).

Il file include:
- nome, tipo, ingredienti, descrizione, prezzo
- embedding calcolato da SentenceTransformers (CPU)

Esempio di esecuzione:
    export DB_NAME=demo_restaurant
    python data/load_menu.py
"""

import json, os, time
from pathlib import Path

import psycopg2, psycopg2.extras            # DB driver
from sentence_transformers import SentenceTransformer   # embedding (CPU)

# ───── CONFIGURAZIONE ───────────────────────────────────────────────
DB = dict(
    dbname   = os.getenv("DB_NAME", "demo_restaurant"),
    user     = os.getenv("DB_USER", "postgres"),
    password = os.getenv("DB_PASS", "postgres"),
    host     = os.getenv("DB_HOST", "localhost"),
    port     = int(os.getenv("DB_PORT", "5432")),
)

DATA_DIR   = Path(__file__).resolve().parent
MENU_JSON  = Path(os.getenv("MENU_JSON", DATA_DIR / "menu.json"))
MODEL_NAME  = "sentence-transformers/all-mpnet-base-v2"   # 768 dim
BATCH_SIZE  = 64                                          # tweak se vuoi

# ───── 1. CARICAMENTO JSON ──────────────────────────────────────────
print(f"• Apro {MENU_JSON} …")
with MENU_JSON.open(encoding="utf-8") as f:
    raw_menu = json.load(f)

print(f"  Trovati {len(raw_menu)} piatti nel JSON")

# ───── 2. COSTRUZIONE TEXT + RIGHE DB ───────────────────────────────
texts, rows = [], []
for item in raw_menu:
    txt = " | ".join([
        item.get("name", ""),
        item.get("type", ""),
        item.get("description", ""),
        ", ".join(item.get("ingredients", []))
    ])
    texts.append(txt)

    rows.append((
        item.get("name", ""),
        item.get("type", ""),
        item.get("ingredients", []),
        item.get("description", ""),
        float(item.get("price", 0)),   # default 0 se manca
        None                           # placeholder embedding
    ))

# ───── 3. CALCOLO EMBEDDING (CPU) ───────────────────────────────────
print(f"• Carico modello '{MODEL_NAME}' (CPU) …")
model = SentenceTransformer(MODEL_NAME, device="cpu")
start = time.time()

print("• Calcolo embedding …")
emb = model.encode(
    texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    device="cpu",
    normalize_embeddings=True
)
print(f"  Fatto in {time.time()-start:.1f} s")

for i, e in enumerate(emb):
    rows[i] = rows[i][:-1] + (e.tolist(),)

# ───── 4. INSERIMENTO BULK IN POSTGRES ──────────────────────────────
print("• Inserisco i dati in PostgreSQL …")
INSERT_SQL = """
INSERT INTO menu (name, type, ingredients, description, price, embedding)
VALUES %s
"""

with psycopg2.connect(**DB) as con, con.cursor() as cur:
    psycopg2.extras.execute_values(
        cur,
        INSERT_SQL,
        rows,
        template="(%s,%s,%s,%s,%s,%s::vector)"
    )
    print(f"  Inseriti {len(rows)} record in tabella menu")

print("✓ Operazione completata!")
