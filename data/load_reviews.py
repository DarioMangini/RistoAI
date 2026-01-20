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

#!/usr/bin/env python3
import os, sys, time
import pandas as pd
from pathlib import Path
import psycopg2, psycopg2.extras

# AGGIUNTA FONDAMENTALE
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.vector_client import get_embedding

DB = dict(
    dbname   = os.getenv("DB_NAME", "demo_restaurant"),
    user     = os.getenv("DB_USER", "postgres"),
    password = os.getenv("DB_PASS", "postgres"),
    host     = os.getenv("DB_HOST", "localhost"),
    port     = int(os.getenv("DB_PORT", "5432")),
)
DATA_DIR   = Path(__file__).resolve().parent
CSV_PATH   = Path(os.getenv("REVIEWS_CSV", DATA_DIR / "recensioni.csv"))

print(f"• Apro {CSV_PATH} …")
df = pd.read_csv(CSV_PATH)
print(f"  Trovate {len(df)} recensioni. Calcolo embedding...")

rows = []
start = time.time()

for _, row in df.iterrows():
    txt = row["recensione"]
    if isinstance(row["piatti"], str):
        txt += " | Piatti: " + row["piatti"]
    
    vector = get_embedding(txt)

    rows.append((
        row["id"],
        int(row["voto"]),
        row["recensione"],
        row["piatti"],
        vector
    ))

print(f"• Calcolo finito in {time.time()-start:.1f} s. Scrivo su DB...")

INSERT_SQL = """
INSERT INTO recensioni (id, voto, recensione, piatti, embedding)
VALUES %s
"""

try:
    with psycopg2.connect(**DB) as con, con.cursor() as cur:
        cur.execute("TRUNCATE TABLE recensioni;")
        psycopg2.extras.execute_values(
            cur,
            INSERT_SQL,
            rows,
            template="(%s,%s,%s,%s,%s::vector)"
        )
        print(f"✓ Inseriti {len(rows)} record in tabella recensioni")
except Exception as e:
    print(f"ERRORE: {e}")
