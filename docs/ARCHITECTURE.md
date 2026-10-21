# Architecture

## System Overview

Brightr is split into two independently deployed services:

| Component | Tech | Hosted On | Responsibility |
|---|---|---|---|
| Frontend | Next.js (React) | Vercel | UI, session workflow, report views |
| Backend | FastAPI (Python) | Render | AI analysis, session persistence, PDF export |
| AI Model | Google Gemini (`gemini-3-flash-preview`) | Google (external API) | Image analysis → structured JSON |
| Vector Index | ChromaDB | Render persistent disk | Historical finding retrieval (RAG) |
| Database | SQLite | Render persistent disk | Sessions, items, findings |
| Image Storage | Local filesystem | Render persistent disk | Uploaded inspection photos |

The frontend **never** calls Gemini directly. All requests to Gemini are proxied through the FastAPI backend so `GEMINI_API_KEY` stays server-side only.

## Request Flow — Image Analysis

```
User uploads image (web/)
        │
        ▼
POST /api/sessions/{id}/images   (Next.js → FastAPI, via INTERNAL_API_URL)
        │
        ▼
session_service.py: save image to /data/storage
        │
        ▼
analysis_service.analyze_image_structured_with_gemini()
        │
        ├─▶ rag_service.retrieve_examples()  → query ChromaDB for top-5 similar
        │        historical findings (from data/inspection_dataset_with_extracted.csv)
        │
        ├─▶ _load_structured_prompt()  → combines:
        │        1. base instruction
        │        2. recommendation_taxonomy.txt (allowed codes)
        │        3. system_prompt (writing style rules)
        │        4. RAG historical examples (style reference)
        │        5. STRUCTURED_SYSTEM_PROMPT_SUFFIX (JSON schema)
        │
        ▼
Gemini API call (image + prompt)
        │
        ▼
parse_gemini_structured_response()  → StructuredInspectionAnalysis
        │
        ▼
Saved to SQLite (models.py: Item)
        │
        ▼
Returned to frontend, rendered in dashboard
```

## Request Flow — Submit & Report

```
User clicks "Submit Inspection"
        │
        ▼
POST /api/sessions/{id}/submit
        │
        ▼
session_service.submit_session(): status → "submitted" (immutable)
        │
        ▼
Session now appears in /reports (ReportsListPage.tsx)
        │
        ▼
GET /api/sessions/{id}/export/pdf   → create_pdf_report() generates PDF on demand
```

## Environment Boundary

```
┌─────────────── Vercel (Frontend) ───────────────┐
│  INTERNAL_API_URL   → points to Render backend   │
│  INTERNAL_API_KEY   → shared secret               │
└───────────────────────────────────────────────────┘
                        │ HTTPS
                        ▼
┌─────────────── Render (Backend) ─────────────────┐
│  GEMINI_API_KEY      → Google Gemini auth         │
│  GEMINI_MODEL         → model name                │
│  DATABASE_URL         → sqlite:////data/brightr.db│
│  STORAGE_ROOT         → /data/storage             │
│  CHROMA_DB_PATH       → /data/chroma_db           │
│  CORS_ORIGINS         → allowed frontend origins   │
└─────────────────────────────────────────────────────┘
```

## Persistent Disk Layout (Render)

```
/data/
├── brightr.db          # SQLite database
├── storage/
│   └── sessions/       # uploaded images, one folder per session
└── chroma_db/          # RAG vector index (rebuilt by start.sh if missing)
```

⚠️ This disk is **not automatically backed up**. For production use, consider migrating to a managed Postgres database and Cloudflare R2 for image storage.
