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

#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
import psycopg2, psycopg2.extras

# AGGIUNTA FONDAMENTALE: Aggiunge la root del progetto al path per importare 'core'
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.vector_client import get_embedding  # <--- Usa il client centralizzato

# Configurazione DB
DB = dict(
    dbname   = os.getenv("DB_NAME", "demo_restaurant"),
    user     = os.getenv("DB_USER", "postgres"),
    password = os.getenv("DB_PASS", "postgres"),
    host     = os.getenv("DB_HOST", "localhost"),
    port     = int(os.getenv("DB_PORT", "5432")),
)

DATA_DIR   = Path(__file__).resolve().parent
MENU_JSON  = Path(os.getenv("MENU_JSON", DATA_DIR / "menu.json"))

print(f"• Apro {MENU_JSON} …")
with MENU_JSON.open(encoding="utf-8") as f:
    raw_menu = json.load(f)

print(f"  Trovati {len(raw_menu)} piatti. Calcolo embedding via Provider configurato...")

rows = []
start = time.time()

for item in raw_menu:
    # Crea il testo da vettorizzare
    txt = " | ".join([
        item.get("name", ""),
        item.get("type", ""),
        item.get("description", ""),
        ", ".join(item.get("ingredients", []))
    ])
    
    # CHIAMA OPENAI (o il modello locale leggero) TRAMITE IL CLIENT UNIFICATO
    # Gestisce automaticamente i ritentativi e la logica
    vector = get_embedding(txt) 

    rows.append((
        item.get("name", ""),
        item.get("type", ""),
        item.get("ingredients", []),
        item.get("description", ""),
        float(item.get("price", 0)),
        vector  # Lista float
    ))

print(f"• Calcolo finito in {time.time()-start:.1f} s. Scrivo su DB...")

INSERT_SQL = """
INSERT INTO menu (name, type, ingredients, description, price, embedding)
VALUES %s
"""

try:
    with psycopg2.connect(**DB) as con, con.cursor() as cur:
        # Svuota la tabella prima di ricaricare per evitare duplicati
        cur.execute("TRUNCATE TABLE menu;")
        
        psycopg2.extras.execute_values(
            cur,
            INSERT_SQL,
            rows,
            template="(%s,%s,%s,%s,%s,%s::vector)"
        )
        print(f"✓ Inseriti {len(rows)} record in tabella menu")
except Exception as e:
    print(f"ERRORE SQL: {e}")