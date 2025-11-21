# RistoAI (demo)

Flask backend for a restaurant AI assistant, sanitized of corporate references and including demo data. It uses Postgres + pgvector for menu/reviews, an external LLM for criteria/chat, and Redis for conversational state.

## Features
- REST API (/api/...) for menu, ingredients, cart, and AI chat.
- Semantic search on menu and reviews via pgvector and an embedding microservice.
- Modular prompts: criteria, reviews, and final response (demo versions included).
- Data loading scripts (data/load_menu.py, data/load_reviews.py) with dummy datasets.

## Requirements
- Python 3.10+
- PostgreSQL 15+ with pgvector extension
- Redis (for chat memory)
- An LLM endpoint compatible with /v1/chat/completions
- An HTTP embedding endpoint (default: local all-mpnet-base-v2)

## Quick Install
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask flask_sqlalchemy pgvector psycopg2-binary requests redis pandas sentence-transformers
```

## Key Environment Variables
```
DB_NAME=demo_restaurant
DB_USER=postgres
DB_PASS=postgres
DB_HOST=localhost
DB_PORT=5432

LLM_URL=http://localhost:8000/v1/chat/completions
LLM_MODEL=google/gemma-3-27b-it
EMB_URL_MPNET=http://localhost:5040/embedding/all-mpnet-base-v2

REDIS_HOST=localhost
REDIS_PORT=6379

API_PREFIX=/api
PROMPTS_DIR=prompts          # optional, default is internal folder
CHAT_PROMPT_FILE=prompts/demo-chat.txt
CRITERIA_PROMPT_BASENAME=demo-criteria
REVIEWS_PROMPT_BASENAME=demo-reviews

# optional for remote fallback calls
CRITERIA_REMOTE_URL=http://localhost:9001/api/criteria
REVIEWS_REMOTE_URL=http://localhost:9001/api/reviews
REMOTE_API_KEY=changeme
```

## Database Setup
1. Create the database and enable pgvector:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Run the app for the first time (creates SQLAlchemy tables) or run `flask shell` to execute `db.create_all()`.

## Loading Demo Data
With the environment active and DB env vars set:
```bash
python data/load_menu.py      # inserts 46 demo dishes with embeddings
python data/load_reviews.py   # inserts 12 demo reviews with embeddings
```

## Starting the Server
```bash
export FLASK_APP=app.py
python app.py  # defaults to exposing on 0.0.0.0:5010
```
Routes are located under `API_PREFIX` (default `/api`),e.g., `POST /api/chat`.

## Chat Call Example
```bash
curl -X POST http://localhost:5010/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": "",
    "project": "demo",
    "conversation_history": [
      {"role": "user", "content": "Mi consigli un uramaki piccante?"}
    ]
  }'
```

## Prompts and Data
- Demo prompts located in `prompts/demo-*.txt`.
- Dummy datasets in `data/menu.json` and `data/recensioni.csv`.

## GUI
A GUI is not included in this repo; the backend is designed to be exposed to an external frontend (web/mobile).


