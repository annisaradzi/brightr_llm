# Brightr — AI-Powered Oil & Gas Inspection Platform

Brightr assists inspection engineers by analyzing equipment photos with Google Gemini and generating professional, engineer-style findings and maintenance recommendations — grounded in 4,700+ historical inspection records via Retrieval-Augmented Generation (RAG).

---

## Architecture Overview

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Frontend       │  HTTPS  │   Backend API     │  HTTPS  │   Google Gemini  │
│   (Next.js)      │────────▶│   (FastAPI)       │────────▶│   gemini-3-flash │
│   Hosted: Vercel │         │   Hosted: Render  │         │                  │
└─────────────────┘         └──────────────────┘         └─────────────────┘
                                      │
                                      ▼
                        ┌─────────────────────────┐
                        │  Render Persistent Disk  │
                        │  /data/brightr.db        │ (SQLite — sessions/items)
                        │  /data/storage/          │ (uploaded images)
                        │  /data/chroma_db/        │ (RAG vector index)
                        └─────────────────────────┘
```

**Key point:** the frontend (Vercel) never talks to Gemini directly. All AI calls go through the FastAPI backend (Render), which keeps `GEMINI_API_KEY` and `INTERNAL_API_KEY` server-side only.

---

## How Analysis Works (RAG Pipeline)

1. Engineer uploads an inspection image via the web UI.
2. Backend receives the image and queries [`rag_service.py`](rag_service.py) for the top-5 most similar historical inspection examples from a ChromaDB index built from `data/inspection_dataset_with_extracted.csv` (4,708 real historical findings).
3. Those examples are injected into the Gemini prompt as **style reference only** (never copied verbatim).
4. Gemini analyzes the image and returns structured JSON: findings, recommendation, rust grade, CoF, priority, equipment type, and bounding-box detections.
5. Result is parsed, saved to SQLite, and displayed in the UI.
6. On "Submit Inspection," the session becomes immutable and appears in **Reports**.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for full technical detail and [`docs/RAG_SYSTEM.md`](docs/RAG_SYSTEM.md) for the RAG pipeline.

---

## Repository Structure

```
brightr_llm/
├── api_server.py              # FastAPI app entrypoint, legacy /api/analyze endpoint
├── session_service.py         # Session/item CRUD, submit/report flow
├── analysis_service.py        # Gemini prompt building + response parsing
├── rag_service.py             # ChromaDB retrieval for historical examples
├── database.py                # SQLAlchemy engine/session (SQLite by default)
├── models.py                  # ORM models (Session, Item)
├── schemas.py                 # Pydantic request/response schemas
├── storage.py                 # Image file storage on disk
├── system_prompt                     # Editable Gemini system prompt (writing style rules)
├── recommendation_taxonomy.txt      # Allowed recommendation codes (TBP, TBR, etc.)
├── scripts/
│   └── build_rag_index.py     # One-time script to embed CSV rows into ChromaDB
├── data/
│   └── inspection_dataset_with_extracted.csv   # 4,708 historical inspection records
├── start.sh                   # Render startup: builds RAG index if missing, then starts uvicorn
├── Dockerfile                 # Backend container definition
├── render.yaml                # Render deployment blueprint
├── docker-compose.yml         # Local full-stack dev (optional)
├── web/                       # Next.js frontend (deployed to Vercel)
└── docs/                      # Architecture & API documentation
```

---

## Local Development

### 1. Backend (FastAPI + Gemini)

```bash
# from repo root
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# copy and fill in your .env
cp .env.example .env
# edit .env: set GEMINI_API_KEY

# (one-time) build the RAG vector index from the CSV
python scripts/build_rag_index.py

# start the backend
uvicorn api_server:app --reload --port 8000 --host 0.0.0.0
```

### 2. Frontend (Next.js)

```bash
cd web
npm install

# point the frontend at your local backend
echo 'INTERNAL_API_URL="http://localhost:8000"' > .env.local

npm run dev
open http://localhost:3000
```

---

## Environment Variables

| Variable | Where | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | Backend | Google Gemini API key (**required**) |
| `GEMINI_MODEL` | Backend | Model name (default: `gemini-3-flash-preview`) |
| `DATABASE_URL` | Backend | SQLAlchemy DB URL (default: local SQLite) |
| `STORAGE_ROOT` | Backend | Directory for uploaded images |
| `CHROMA_DB_PATH` | Backend | Path to ChromaDB vector index (default: `data/chroma_db`) |
| `RAG_CSV_PATH` | Backend | Path to historical CSV used to build the RAG index |
| `CORS_ORIGINS` | Backend | Comma-separated allowed frontend origins |
| `INTERNAL_API_KEY` | Backend + Frontend | Shared secret between Next.js and FastAPI |
| `INTERNAL_API_URL` | Frontend | Public/local URL of the FastAPI backend |

Never commit real values for `GEMINI_API_KEY` or `INTERNAL_API_KEY` — both `.env` and `.env.local` are gitignored.

---

## Deployment

- **Backend** → Render, via [`render.yaml`](render.yaml) blueprint. Push to your branch, then trigger a deploy from the Render dashboard. On first boot, `start.sh` builds the RAG index on the persistent disk if it doesn't exist yet.
- **Frontend** → Vercel. Set `INTERNAL_API_URL` and `INTERNAL_API_KEY` as environment variables in the Vercel project settings (Preview and Production separately — never test with Production).

Full details: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

---

## Customizing the AI's Writing Style

Edit [`system_prompt`](system_prompt) — a plain text file loaded at request time. It defines:
- Required finding format: `(V1) COMPONENT - description. (L:likelihood C:consequence)`
- Which defects/components to look for
- Recommendation wording conventions

After editing, **restart the backend** (`uvicorn` does not hot-reload plain text files, only `.py` files).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `API key not valid` (400) | `GEMINI_API_KEY` is empty or a placeholder | Get a real key from https://aistudio.google.com/app/apikey and set it in `.env` |
| System prompt changes don't apply | Backend wasn't restarted | Restart `uvicorn` — plain text files aren't hot-reloaded |
| Findings appear as paragraphs, not `(V1) ...` format | Old cached prompt or Gemini not following schema | Confirm [`system_prompt`](system_prompt) and `STRUCTURED_SYSTEM_PROMPT_SUFFIX` in `analysis_service.py` both enforce the format |
| `Server misconfiguration: set INTERNAL_API_URL` | Frontend env var missing | Set `INTERNAL_API_URL` in Vercel (Preview) or `web/.env.local` (local dev) |
| RAG examples not appearing in prompt | ChromaDB index not built | Run `python scripts/build_rag_index.py` |

More: see [`docs/REPO_SUMMARY.md`](docs/REPO_SUMMARY.md)
