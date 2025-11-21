#!/usr/bin/env python3
"""
load_reviews_pg.py
───────────────────────────────────────────────────────────────────────────────
Carica `recensioni_sushi.csv` in PostgreSQL (`tabella recensioni`)
aggiungendo l’embedding SBERT (768 dim) calcolato su CPU.

Il file CSV deve contenere:
- id (UUID), voto (1–5), recensione (testo), piatti (lista serializzata)

Esempio di esecuzione:
    export DB_NAME=demo_restaurant
    python data/load_reviews.py
"""

import os, time
import pandas as pd
from pathlib import Path
import psycopg2, psycopg2.extras
from sentence_transformers import SentenceTransformer

# ───── CONFIGURAZIONE ───────────────────────────────────────────────
DB = dict(
    dbname   = os.getenv("DB_NAME", "demo_restaurant"),
    user     = os.getenv("DB_USER", "postgres"),
    password = os.getenv("DB_PASS", "postgres"),
    host     = os.getenv("DB_HOST", "localhost"),
    port     = int(os.getenv("DB_PORT", "5432")),
)
DATA_DIR   = Path(__file__).resolve().parent
CSV_PATH    = Path(os.getenv("REVIEWS_CSV", DATA_DIR / "recensioni.csv"))
MODEL_NAME  = "sentence-transformers/all-mpnet-base-v2"
BATCH_SIZE  = 64

# ───── 1. CARICAMENTO CSV ───────────────────────────────────────────
print(f"• Apro {CSV_PATH} …")
df = pd.read_csv(CSV_PATH)
print(f"  Trovate {len(df)} recensioni nel CSV")

# ───── 2. COSTRUZIONE TEXT + RIGHE DB ───────────────────────────────
texts, rows = [], []
for _, row in df.iterrows():
    # Costruisce testo da usare per embedding
    txt = row["recensione"]
    if isinstance(row["piatti"], str):
        txt += " | Piatti: " + row["piatti"]
    texts.append(txt)

    rows.append((
        row["id"],
        int(row["voto"]),
        row["recensione"],
        row["piatti"],
        None
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

# Inserisce embedding nei record
for i, e in enumerate(emb):
    rows[i] = rows[i][:-1] + (e.tolist(),)

# ───── 4. INSERIMENTO BULK IN POSTGRES ──────────────────────────────
print("• Inserisco i dati in PostgreSQL …")
INSERT_SQL = """
INSERT INTO recensioni (id, voto, recensione, piatti, embedding)
VALUES %s
"""

with psycopg2.connect(**DB) as con, con.cursor() as cur:
    psycopg2.extras.execute_values(
        cur,
        INSERT_SQL,
        rows,
        template="(%s,%s,%s,%s,%s::vector)"
    )
    print(f"  Inseriti {len(rows)} record in tabella recensioni")

print("✓ Operazione completata!")
