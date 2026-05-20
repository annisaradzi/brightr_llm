# brightr_llm — Full Repository Summary

## What This Project Is

**brightr.AI** is an **AI-powered industrial corrosion inspection platform** for oil & gas facilities. Engineers upload photos of equipment (pipes, flanges, pressure vessels, structural steel), and the system uses **Google Gemini Vision AI** to automatically detect corrosion, grade its severity, produce findings/recommendations, draw bounding boxes around defect regions, and generate professional PDF inspection reports.

---

## Architecture Overview

The app is a **two-tier system** with a clear backend/frontend split:

```
┌─────────────────────────────────────┐
│  FRONTEND: Next.js 15 (port 3000)  │
│  React 19 + Tailwind CSS 4         │
│  ┌───────────────────────────────┐  │
│  │  Next.js API Routes (BFF)    │──┤── Browser calls /api/* on same origin
│  │  Proxies to FastAPI backend  │  │
│  └───────────────────────────────┘  │
└──────────────┬──────────────────────┘
               │ HTTP (X-Internal-Key header)
               ▼
┌─────────────────────────────────────┐
│  BACKEND: FastAPI (port 8000)       │
│  Python 3.12 + SQLAlchemy + Pillow  │
│  ┌─────────────┐  ┌──────────────┐  │
│  │ SQLite DB   │  │ Filesystem   │  │
│  │ brightr.db  │  │ storage/     │  │
│  └─────────────┘  └──────────────┘  │
└──────────────┬──────────────────────┘
               │ HTTPS API calls
               ▼
┌─────────────────────────────────────┐
│  Google Gemini Vision API           │
│  (gemini-3-flash-preview)           │
└─────────────────────────────────────┘
```

---

## Backend (Python / FastAPI)

**Entry point:** `api_server.py` — run via `uvicorn api_server:app --reload --port 8000`

### Files and Responsibilities

| File | Purpose |
|------|---------|
| `api_server.py` | FastAPI app with all REST endpoints, CORS setup, lifespan DB init |
| `analysis_service.py` | Gemini AI integration, prompt engineering, JSON parsing, PDF report generation |
| `session_service.py` | Business logic — CRUD for sessions/items, analysis orchestration, submission workflow, report listing/approval |
| `models.py` | SQLAlchemy ORM models (`InspectionSession`, `InspectionItem`) |
| `schemas.py` | Pydantic DTOs for request/response validation |
| `database.py` | SQLAlchemy engine setup, session factory, DB migration helper |
| `storage.py` | Filesystem operations — save images as JPEG, write sidecar files (findings, bounding boxes, manifest) |
| `recommendation_taxonomy.txt` | Domain reference taxonomy for the AI prompt (corrosion grading codes, recommendation codes) |

### API Endpoints

**Session workflow:**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/sessions` | Create a new inspection session (status: `draft`) |
| `GET` | `/api/sessions/{id}` | Get session with all items |
| `POST` | `/api/sessions/{id}/images` | Upload inspection photos (multipart) |
| `POST` | `/api/sessions/{id}/analyze` | Run Gemini AI analysis on all images |
| `PATCH` | `/api/sessions/{id}/items/{itemId}` | Edit AI-generated findings (human review) |
| `DELETE` | `/api/sessions/{id}/items/{itemId}` | Remove uploaded image (pending/failed only, draft session) |
| `POST` | `/api/sessions/{id}/submit` | Finalize session, generate PDF, write sidecar files |
| `GET` | `/api/sessions/{id}/items/{itemId}/image` | Serve stored JPEG image |

**Reports workflow:**

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/reports` | List submitted reports (with filtering, pagination, sorting) |
| `POST` | `/api/reports/bulk-delete` | Delete multiple reports (`{ reportIds: string[] }`) |
| `GET` | `/api/reports/{id}` | Report detail with all findings |
| `DELETE` | `/api/reports/{id}` | Delete report (DB + storage) |
| `POST` | `/api/reports/{id}/approve` | Approve a report |
| `POST` | `/api/reports/{id}/request-changes` | Send report back with comments |
| `GET` | `/api/reports/{id}/pdf` | Download executive summary PDF |

**Legacy:**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/analyze` | Standalone single-image analysis (returns PDF as base64) |

### Security

- All endpoints require `X-Internal-Key` header (HMAC-compared against `INTERNAL_API_KEY` env var)
- The frontend's BFF layer injects this key server-side so it's never exposed to the browser

---

## The AI Engine (`analysis_service.py`)

This is the core intelligence of the application.

### Model

Uses **Google Gemini** (`gemini-3-flash-preview` by default, configurable via `GEMINI_MODEL` env var) through the `google-generativeai` Python SDK.

### Two Analysis Modes

1. **Structured mode** (`analyze_image_structured_with_gemini`) — Used by the session workflow. Returns a rich JSON schema with:
   - `findingsText`, `recommendationText`
   - `rustGrade` (Ri1 / Ri2 / R3 / R4 / R5)
   - `cof` (1–5)
   - `findingsPriority`, `sapPriority`
   - `equipmentType`
   - `recommendationCode` (TBR / TBRy / TBP / TBM / TBS)
   - Boolean flags: `furtherInspection`, `openInsulation`, `scaffold`
   - `aiConfidence`
   - `detections` with normalized bounding boxes

2. **General mode** (`analyze_image_with_gemini`) — Used by the legacy `/api/analyze` endpoint. Returns summary, findings list, recommendations list, and detections.

### Prompt Engineering

A detailed system prompt instructs Gemini to act as an "oil & gas visual inspection engineer." The prompt loads a `recommendation_taxonomy.txt` file with domain-specific grading codes. It enforces strict JSON-only output.

### PDF Generation

Uses **ReportLab** to produce professional branded PDF reports with the brightr.AI logo (generated programmatically via PIL), findings tables, detection coordinates, and metadata.

---

## Database

**Yes, there IS a database** — **SQLite** by default.

- **File:** `brightr.db` in the project root (auto-created on first run)
- **ORM:** SQLAlchemy 2.0 with mapped columns
- **Configurable:** `DATABASE_URL` env var, defaults to `sqlite:///./brightr.db`, supports other SQL databases
- **Migration:** `_ensure_session_columns()` does lightweight `ALTER TABLE` for column additions (SQLite-specific)

### Two Tables

#### `inspection_sessions` — The inspection report container

| Column | Type | Notes |
|--------|------|-------|
| `id` | String(36) | UUID primary key |
| `status` | String(20) | `draft` / `submitted` / `in_review` / `approved` |
| `created_by` | String(320) | User email |
| `system_report_number` | String(32) | Auto-generated `RF-XXXXXXXX` |
| `user_report_number` | String(64) | Optional user-provided |
| `plant` | String(128) | Facility name |
| `system_code` | String(128) | System identifier |
| `preparer_name` | String(128) | |
| `reviewer_name` | String(128) | |
| `approver_name` | String(128) | |
| `executive_summary` | Text | Auto-generated or user-provided |
| `pdf_path` | String(512) | Path to generated PDF |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |
| `submitted_at` | DateTime | |
| `reviewed_at` | DateTime | |
| `approved_at` | DateTime | |
| `review_comment` | Text | Reviewer feedback |

#### `inspection_items` — Individual image findings (many per session)

| Column | Type | Notes |
|--------|------|-------|
| `id` | String(36) | UUID primary key |
| `session_id` | String(36) | FK to `inspection_sessions` |
| `sort_order` | Integer | Display order |
| `code` | String(32) | e.g. `IMG-001` |
| `image_path` | String(512) | Filesystem path to JPEG |
| `image_width` / `image_height` | Integer | |
| `ai_findings` | Text | Raw AI output |
| `ai_recommendation` | Text | Raw AI output |
| `ai_bounding_boxes_json` | Text | JSON array of detections |
| `ai_confidence` | Float | 0–1 |
| `ai_analyzed_at` | DateTime | |
| `ai_raw_json` | Text | Full Gemini response + AI snapshot |
| `findings` | Text | Human-editable (starts as AI copy) |
| `recommendation` | Text | Human-editable |
| `rust_grade` | String(8) | Ri1 / Ri2 / R3 / R4 / R5 |
| `cof` | Integer | 1–5 consequence of failure |
| `findings_priority` | String(16) | low / medium / high |
| `sap_priority` | String(16) | low / medium / high |
| `equipment_type` | String(32) | piping / pressure_vessel / flange / structural / other |
| `equipment_id` | String(64) | e.g. `EQ-5C9D8D54-001` |
| `recommendation_code` | String(8) | TBR / TBRy / TBP / TBM / TBS |
| `further_inspection` | Boolean | |
| `open_insulation` | Boolean | |
| `scaffold` | Boolean | |
| `review_status` | String(20) | unreviewed / in_progress / confirmed |
| `analysis_status` | String(20) | pending / complete / failed |
| `analysis_error` | Text | Error message if analysis failed |

---

## File Storage (`storage.py`)

Stores files locally on the filesystem (in addition to the DB).

- **Root:** `storage/` directory (configurable via `STORAGE_ROOT` env var)
- **Structure:**

```
storage/
└── sessions/
    └── {session_uuid}/
        ├── {item_uuid}.jpg              # Original uploaded image (converted to JPEG)
        ├── {item_uuid}_findings.txt     # Text sidecar with findings + recommendation
        ├── {item_uuid}_bboxes.json      # Bounding box coordinates from AI
        ├── manifest.json                # Session manifest with all items and report metadata
        └── executive_report.pdf         # Generated PDF report
```

The DB stores structured data and references; the filesystem stores binary assets (images, PDFs) and sidecar exports.

---

## Frontend (Next.js 15 / React 19)

**Location:** `web/` directory

### Tech Stack

- **Next.js 15.5** with Turbopack (dev mode)
- **React 19.1**
- **Tailwind CSS 4**
- **jose** (JWT verification for session auth)
- No additional UI libraries — all components are hand-built

### Architecture: BFF (Backend-For-Frontend) Pattern

The frontend does **NOT** call the FastAPI backend directly from the browser. Instead:

1. **Browser** calls Next.js API routes at `/api/*` (same origin, port 3000)
2. **Next.js API routes** (`web/src/app/api/sessions/...`) act as a proxy/BFF layer
3. These routes **verify the user session** (JWT cookie), then **forward the request** to the FastAPI backend at `http://127.0.0.1:8000` with the `X-Internal-Key` header
4. The `internal-api.ts` utility handles the proxying logic, key injection, and error mapping

This means the `INTERNAL_API_KEY` and `GEMINI_API_KEY` are **never exposed** to the browser.

### Key Frontend Files

| File | Purpose |
|------|---------|
| `web/src/components/BrightrDashboard.tsx` | Main inspection dashboard — the primary UI. Upload images, view AI findings, edit fields, submit |
| `web/src/components/BrightrDashboardTemplate.tsx` | Alternate "spreadsheet" layout (built but **not wired** to any route) |
| `web/src/api/sessions.ts` | Client-side API functions (call same-origin `/api/*` routes) |
| `web/src/api/reports.ts` | Reports API client; used by `/reports` pages |
| `web/src/app/reports/*` | Reports list and detail UI (v2 mockup) |
| `DELETE /api/sessions/{id}/items/{itemId}` | Remove pending/failed upload before analyze |
| `web/src/api/client.ts` | Generic `apiFetch` wrapper with auth redirect on 401 |
| `web/src/types/inspection.ts` | TypeScript interfaces mirroring backend schemas |
| `web/src/lib/internal-api.ts` | Server-side BFF helpers (proxy to FastAPI, inject auth headers) |
| `web/src/lib/session.ts` | JWT cookie creation/verification (`brightr_session`) |
| `web/src/lib/auth-users.ts` | Demo credential validation from `AUTH_USERS` env |
| `web/src/middleware.ts` | Edge auth gate — protects `/` and `/reports/*`, redirects to `/login` |
| `web/src/app/api/sessions/*/route.ts` | Next.js API routes that proxy to FastAPI (10 routes) |
| `web/src/app/login/page.tsx` | Login form with email/password |
| `web/src/app/page.tsx` | Root page — renders `BrightrDashboard` |

### UI Flow (Inspection Workflow)

1. User lands on dashboard, a new session is auto-created
2. User uploads corrosion photos via drag-and-drop or file picker
3. User clicks "Analyze" — triggers Gemini AI analysis on all images
4. AI returns per-image findings: rust grade, priority, recommendations, bounding boxes overlaid on image
5. User reviews and edits AI findings (text, grades, codes, flags)
6. The UI tracks which fields the user modified vs. original AI output (`editedFields`)
7. User fills report metadata (plant, system code, preparer/reviewer/approver) and submits
8. Submission generates a PDF report and writes all sidecar files

### Reports (Partial Implementation)

- Client code (`reports.ts`) and types exist for list/detail/approve/request-changes
- Middleware protects `/reports/*` routes
- **No pages or BFF routes exist yet** in `src` — users would 404

### State Management

- Local React hooks (`useState`, `useRef`, `useMemo`, `useCallback`)
- No global store, no React Query, no context providers
- 800ms debounced auto-save on field edits
- URL state: `?finding=<itemId>` for selected finding

---

## Authentication

| Layer | Mechanism |
|-------|-----------|
| **Browser → Next.js** | JWT in httpOnly cookie (`brightr_session`), HS256 signed with `AUTH_SECRET` |
| **Next.js → FastAPI** | `X-Internal-Key` header (shared secret), `X-User-Email` header (from JWT) |
| **Login** | `POST /api/auth/login` — validates against `AUTH_USERS` JSON env var |

---

## Environment Variables

| Variable | Used By | Purpose |
|----------|---------|---------|
| `GEMINI_API_KEY` | Backend | Google Gemini API authentication |
| `GEMINI_MODEL` | Backend | Model name (default: `gemini-3-flash-preview`) |
| `DATABASE_URL` | Backend | SQLAlchemy connection string (default: `sqlite:///./brightr.db`) |
| `STORAGE_ROOT` | Backend | Filesystem storage root (default: `storage`) |
| `CORS_ORIGINS` | Backend | Allowed CORS origins (default: `localhost:3000`) |
| `INTERNAL_API_KEY` | Both | Shared secret for BFF-to-backend auth |
| `INTERNAL_API_URL` | Frontend | FastAPI URL for the BFF proxy (default: `http://127.0.0.1:8000`) |
| `AUTH_SECRET` | Frontend | JWT signing secret (min 16 chars) |
| `AUTH_USERS` | Frontend | JSON `{"email":"password"}` for demo login |
| `BRIGHTR_PDF_LOGO` | Backend | Optional custom logo path for PDF reports |

---

## Infrastructure

- **No Docker, no docker-compose, no cloud deployment config** in the repo
- **Purely local development setup**: run FastAPI on port 8000, Next.js on port 3000
- **SQLite file-based database** (no Postgres/MySQL)
- **Local filesystem storage** (no S3/blob storage)
- The frontend's `internal-api.ts` has production safety checks (rejects localhost URLs in production) and mentions Vercel in error messages, suggesting **Vercel** is the intended frontend deployment target
- Backend would need a separate host (any Python server with uvicorn)

---

## Domain Model Summary

This is an **oil & gas corrosion inspection** tool. The key domain concepts:

| Concept | Values / Scale |
|---------|---------------|
| **Rust Grades** | Ri1 (best) → R5 (worst), per ISO 8501 |
| **Recommendation Codes** | TBR (repair), TBRy (rectify), TBP (paint), TBM (monitor), TBS (strip insulation) |
| **CoF (Consequence of Failure)** | 1–5 scale |
| **Equipment Types** | piping, pressure_vessel, flange, structural, other |
| **Priorities** | low, medium, high (for both findings and SAP integration) |
| **Action Flags** | `furtherInspection`, `openInsulation`, `scaffold` (boolean) |
| **Session Lifecycle** | `draft` → `submitted` → `in_review` → `approved` |

---

## Session Status Workflow

```
draft ──(submit)──▶ submitted ──(review)──▶ in_review ──(approve)──▶ approved
                         ▲                                    │
                         └──────(request changes)─────────────┘
```

- `draft`: Upload, analyze, patch allowed
- `submitted`: Locked for edits; appears in reports list; manifest + PDF written
- `in_review`: Report under review
- `approved`: Terminal state

---

## Dependency Graph

```
api_server.py
 ├── database.py → models.py
 ├── schemas.py
 ├── session_service.py
 │    ├── analysis_service.py → google.generativeai, reportlab, PIL
 │    ├── models.py
 │    └── storage.py
 └── analysis_service.py (legacy /api/analyze only)

app.py (Streamlit) → analysis_service.py

web/ (Next.js BFF)
 └── /api/sessions/* routes → HTTP proxy → FastAPI :8000
```

---

## How to Run

```bash
# Backend
pip install -r requirements.txt
# Create .env with at minimum: GEMINI_API_KEY=your-key
uvicorn api_server:app --reload --port 8000

# Frontend
cd web
npm install
npm run dev
# Opens on http://localhost:3000
```

---

## Python Dependencies (`requirements.txt`)

| Package | Role |
|---------|------|
| `streamlit` | Legacy Streamlit UI (`app.py`) |
| `google-generativeai` | Gemini API client |
| `reportlab` | PDF report generation |
| `python-dotenv` | `.env` file loading |
| `Pillow` | Image processing |
| `pandas` | Streamlit data tables |
| `fastapi` + `uvicorn` | HTTP API server |
| `python-multipart` | Multipart file upload support |
| `sqlalchemy` | ORM / database layer |

## Frontend Dependencies (`web/package.json`)

| Package | Role |
|---------|------|
| `next@15.5` | App framework |
| `react@19.1` + `react-dom` | UI library |
| `jose@6` | JWT signing/verification |
| `tailwindcss@4` | Utility CSS |
| `typescript@5` | Type checking |
