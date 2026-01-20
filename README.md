# RistoAI

Flask backend for a restaurant AI assistant. This version is designed to be **easily runnable locally** (Standalone), removing the dependency on complex external microservices found in previous versions.

Natively supports:
- **OpenAI** (GPT-4o, text-embedding-3) for an immediate setup.
- **Local CPU** (SentenceTransformers) for free embeddings without a GPU.
- **Ollama** (via compatible APIs) for local LLMs.

## Features
- **REST API** (`/api/...`) for menu, ingredients, cart management, and AI chat.
- **Hybrid Semantic Search**: Uses `pgvector` on PostgreSQL. Embeddings are calculated internally (via CPU or external APIs).
- **Modular Architecture**: Monolithic backend prepared for scalability.
- **Dynamic Prompts**: Advanced management of prompts for criteria extraction, reviews, and final responses.
- **Docker Ready**: Complete setup with a single command.

## Requirements
- Docker & Docker Compose (Recommended)
- *Or:* Python 3.10+ and PostgreSQL 15+ with `vector` extension enabled.

## 🚀 Quick Start (Docker) - Recommended

This is the fastest way to test the project without installing Python libraries on your host machine.

### 1. Configuration
Create a `.env` file in the project root:

```bash
# Choose embedding provider: 'openai' or 'local_cpu'
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-key-here

# LLM Configuration (Example with OpenAI)
LLM_URL=https://api.openai.com/v1/chat/completions
LLM_MODEL=gpt-4o-mini
# LLM_API_KEY=${OPENAI_API_KEY}  # Optional if using the same key as above

# Database (Internal to Docker)
DB_NAME=demo_restaurant
DB_USER=postgres
DB_PASS=password
DB_HOST=db
DB_PORT=5432

```

### 2. Start

```bash
docker-compose up --build -d

```

Wait for the containers (`ristoai-app`, `db`, `redis`) to be fully active.

### 3. Load Demo Data (Important!)

The database is created empty. You must populate it by running the scripts **inside** the container:

```bash
# Enter the container
docker exec -it ristoai-app-1 bash

# Run data loading (will use OpenAI or CPU based on your config)
python data/load_menu.py
python data/load_reviews.py

# Exit the container
exit

```

### 4. Test

The server is running at `http://localhost:5010`.

**Chat Example:**

```bash
curl -X POST http://localhost:5010/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "project": "demo",
    "sessionid": "session-1",
    "conversation_history": [
      {"role": "user", "content": "Hi, can you recommend a vegan sushi?"}
    ]
  }'

```

---

## 🛠 Manual Installation (Without Docker)

If you prefer running everything on your host (requires local Postgres installed and configured):

1. **Database**: Ensure Postgres 15+ is running on port 5432 and create the DB:
```sql
CREATE DATABASE demo_restaurant;
\c demo_restaurant
CREATE EXTENSION vector;

```


2. **Python Env**:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```


3. **Load Data**:
```bash
export DB_HOST=localhost
export DB_PASS=your_password
# ... export other env vars (see Docker section)
python data/load_menu.py
python data/load_reviews.py

```


4. **Start Server**:
```bash
python app.py

```



## Key Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `EMBEDDING_PROVIDER` | `local_cpu` | `openai` uses remote APIs, `local_cpu` uses internal SentenceTransformers. |
| `OPENAI_API_KEY` | - | Required if using `openai` provider. |
| `LLM_URL` | (localhost) | Endpoint for chat completions (e.g., OpenAI, Ollama, vLLM). |
| `LLM_MODEL` | `google/gemma...` | Model name to pass to the API. |
| `DB_PORT` | `5432` | Internal DB port. Note: Docker exposes port 5433 externally to avoid conflicts. |

## Project Structure

```
└── ristoai/
    ├── app.py                  # Flask Entry point
    ├── core/
    │   ├── vector_client.py    # Unified Embedding management (OpenAI/Local)
    │   ├── db.py               # SQLAlchemy init
    │   └── models.py           # Table definitions (Menu, Reviews)
    ├── chat_services/          # Chat business logic
    ├── data/                   # Loading scripts and JSON/CSV datasets
    ├── prompts/                # LLM Prompt templates
    ├── routes/                 # API Endpoints
    └── ...

```

## GUI

A GUI is not included in this repo; the backend is designed to be exposed to an external frontend (web/mobile). 

---

**Author**: Mangini Dario
