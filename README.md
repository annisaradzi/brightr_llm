# Photo Analysis Pipeline

Analyzes images with Google Gemini (vision), returns structured JSON (summary, findings, recommendations, optional VLM detection boxes), and generates PDF reports. You can use **Streamlit** (`app.py`), the **FastAPI** service (`api_server.py`) for the **brightr.AI** Next.js UI in `web/`, or both.

## Features

- 📸 **Image Upload**: Support for PNG, JPG, JPEG, and WEBP formats (up to 10MB)
- 🤖 **AI-Powered Analysis**: Uses Google Gemini Vision API for intelligent image analysis
- 📊 **Structured Output**: Extracts findings and recommendations in a structured JSON format
- 📋 **Tabulated Results**: Displays findings and recommendations in easy-to-read tables
- 📄 **PDF Report Generation**: Automatically generates professional PDF reports with formatted tables
- 💾 **Download Reports**: One-click download of generated PDF reports

## Prerequisites

- Python 3.10 or higher
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your API key**:
   - Copy `.env.example` to `.env`:
     ```bash
     copy .env.example .env  # Windows
     cp .env.example .env    # macOS/Linux
     ```
   - Edit `.env` and set your Gemini API key:
     ```
     GEMINI_API_KEY=your-actual-api-key-here
     ```

## Usage

### Option A: Streamlit UI

1. **Start the Streamlit application**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to the URL shown (typically `http://localhost:8501`)

3. **Upload an image**:
   - Click "Browse files" or drag and drop an image
   - Supported formats: PNG, JPG, JPEG, WEBP
   - Maximum file size: 10MB

4. **Analyze the image**:
   - Click the "Analyze image" button
   - Wait for the AI analysis to complete

5. **Review results**:
   - View the executive summary
   - Browse findings in the table
   - Review recommendations in the table

6. **Download PDF report**:
   - Click "Download PDF report" button
   - The report includes all analysis data in a formatted PDF

### Inspection sessions (Phase 1)

The Next.js **New Analysis** UI uses persisted inspection sessions:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | SQLite default: `sqlite:///./brightr.db` |
| `STORAGE_ROOT` | Image/sidecar root (default `storage`) |
| `GEMINI_API_KEY` | Required for AI analysis (sessions and `/api/analyze`) |
| `INTERNAL_API_KEY` | Optional; required by Next BFF when set |

**FastAPI endpoints:** `POST/GET /api/sessions`, upload images, analyze, PATCH item, submit. See [docs/PHASE1_API_CONTRACT.md](docs/PHASE1_API_CONTRACT.md).

**Run locally (two processes):**

```bash
# Terminal 1 — FastAPI (set GEMINI_API_KEY in .env)
uvicorn api_server:app --reload --port 8000

# Terminal 2 — Web
cd web && npm run dev
```

Session analysis (`POST /api/sessions/{id}/analyze`) uses **Google Gemini** structured vision. The in-house VLM path in [`vlm/`](vlm/) is present but **commented out** in the API for now.

Legacy `POST /api/analyze` (single-image Gemini + PDF) is available for compatibility.

### Option B: brightr.AI Next.js + FastAPI

1. **Install Python dependencies** (from the repo root, with your venv active):
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment** — set `GEMINI_API_KEY` in `.env` (see `.env.example`).

3. **Start the API** (terminal 1):
   ```bash
   uvicorn api_server:app --reload --port 8000
   ```
   - Health check: `GET http://127.0.0.1:8000/health`
   - Session analysis: `POST http://127.0.0.1:8000/api/sessions/{id}/analyze`
   - Legacy analyze: `POST http://127.0.0.1:8000/api/analyze`

4. **Start the web app** (terminal 2):
   ```bash
   cd web
   copy .env.example .env.local
   # Windows: use `copy` as above. macOS/Linux: cp .env.example .env.local
   # Edit .env.local if the API is not on http://127.0.0.1:8000
   npm install
   npm run dev
   ```
   Open `http://localhost:3000`, upload an image, run analysis, then download the PDF from the UI.

**Bounding boxes:** Detections with normalized `0–1` boxes are produced by **Gemini** in structured JSON (see `recommendation_taxonomy.txt` / structured prompt). **CORS** for the API is controlled by `CORS_ORIGINS` in `.env` (defaults allow the Next.js dev origin).

### VLM Flask service (`vlm/`) — optional, not wired in API

The Moondream2 service under `vlm/` can be run separately for experiments (`python server.py` on port 5001). FastAPI session analyze does **not** call it while VLM routing is commented out.

## Deployment

The recommended topology is **hybrid**:

- **Next.js (`web/`)** → Vercel (native build, no Docker).
- **FastAPI (`api_server.py`)** → Render as a Docker container with a persistent disk mounted at `/data` for SQLite + uploaded images + generated PDFs.

Vercel is intentionally not used for the backend: it does not run Docker, has a strict 10 s / 60 s function ceiling (Hobby / Pro), a 4.5 MB request-body cap, and an ephemeral filesystem — all of which conflict with this service's long Gemini calls, multi-image uploads, persistent SQLite, and on-disk PDF generation.

### Local: build and run the backend container

```bash
copy .env.example .env          # Windows
cp .env.example .env            # macOS/Linux
# fill in GEMINI_API_KEY (and INTERNAL_API_KEY if your web app sets one)

docker compose up --build
# API:        http://localhost:8000
# Healthcheck: http://localhost:8000/health
# Volume:     ./.data/  (SQLite + storage/)
```

The first `docker compose up` creates `./.data/brightr.db` and `./.data/storage/`. Both survive `docker compose down`; delete `./.data/` to reset.

Point the Next.js dev server at the container with `INTERNAL_API_URL=http://localhost:8000` in `web/.env.local`.

### Render: deploy the FastAPI backend (Docker)

1. Push to GitHub.
2. In Render: **New → Blueprint** → pick this repo. Render reads [`render.yaml`](render.yaml) and provisions:
   - Web Service `brightr-api` on the Starter plan, Docker runtime.
   - A 1 GB persistent disk `brightr-data` mounted at `/data`.
   - Healthcheck on `GET /health`.
3. When prompted, set the secret env vars:
   - `GEMINI_API_KEY` — Gemini key.
   - `INTERNAL_API_KEY` — shared secret; must match the value you'll put on Vercel.
   - `CORS_ORIGINS` — your Vercel URL(s), comma-separated (e.g. `https://brightr.vercel.app`).
4. Deploy. Copy the resulting URL (e.g. `https://brightr-api.onrender.com`).

### Vercel: deploy the Next.js frontend

In the Vercel project (root `web/`) set:

| Variable | Value |
|----------|-------|
| `INTERNAL_API_URL` | `https://brightr-api.onrender.com` (no trailing slash) |
| `INTERNAL_API_KEY` | same value as on Render |
| `AUTH_SECRET` | random ≥16 chars |
| `AUTH_USERS` | JSON map of demo users |

Detailed Vercel checklist (function durations, body limits, build settings): [`web/VERCEL.md`](web/VERCEL.md).

### Production realities (read this before you deploy)

- **Render Starter is the floor** (~$7/mo). Render Free has no disks and sleeps, which would lose the SQLite DB and uploaded images on every cold start. The `render.yaml` pins `plan: starter` so deploys fail fast if you try to downgrade.
- **Vercel timeouts.** Session analyze can run >10 s for multi-image batches. Hobby plans cap functions at 10 s — upgrade to Pro (60 s) or move the analyze trigger to direct browser-to-Render calls if you stay on Hobby.
- **Vercel request body cap is 4.5 MB.** Image uploads currently flow through the Next.js proxy. If a single upload approaches that ceiling, switch the upload route to a presigned direct upload to Render, or chunk uploads.
- **No automatic backups.** SQLite on a Render disk is durable across restarts but is not backed up. For anything resembling production: schedule a nightly `sqlite3 backup` to S3, or migrate to a managed Postgres + object storage (see "Upgrade path" below).
- **Single worker by design.** The Dockerfile runs `uvicorn ... --workers 1` because SQLite handles concurrent writes poorly. Don't bump workers without first switching the DB.
- **Disk capacity.** 1 GB holds roughly a few thousand JPEG findings plus PDFs. Monitor and bump `sizeGB` in `render.yaml` before you hit the wall — Render does not auto-expand.
- **CORS only matters if the browser hits Render directly.** Production traffic is server-to-server through the Next.js Route Handlers, which set `X-Internal-Key` and bypass CORS. Set `CORS_ORIGINS` mainly for debugging tools or future direct uploads.
- **Secret hygiene.** `.env`, `.env.local`, and the `.data/` volume are in `.gitignore`; `.dockerignore` also blocks them. Never commit a real `INTERNAL_API_KEY` or `GEMINI_API_KEY`.

### Upgrade path (when SQLite + disk stops being enough)

1. Replace `DATABASE_URL` with a managed Postgres URL (Neon, Supabase, Render Postgres). SQLAlchemy migrations should be near-drop-in.
2. Replace `STORAGE_ROOT` with an S3/R2 bucket; swap `storage.py` for an object-storage adapter and have PDFs/JPEGs uploaded with presigned URLs.
3. Bump Uvicorn `--workers` once writes no longer hit SQLite.
4. Add a separate worker process for `/analyze` and put it behind a queue if request fan-out grows.

## Customizing the System Prompt

The application uses a system prompt to guide the AI analysis. You can customize it:

1. **Edit `system_prompt` file**:
   - Modify the prompt to change the analysis focus or output format
   - The prompt should request JSON output with `summary`, `findings`, `recommendations`, and optional `detections` (see the file for the schema)

2. **Default prompt**:
   - If `system_prompt` file doesn't exist, the app uses a built-in default prompt
   - The default is optimized for oil & gas corrosion inspection

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Your Google Gemini API key (required for session analyze and `/api/analyze`)
- `GEMINI_MODEL`: Model to use (default in code: `gemini-3-flash-preview`; override as needed)
- `VLM_ENDPOINT_URL`: Only used when VLM routing is re-enabled in `session_service.py` (not active now)
- `CORS_ORIGINS`: Comma-separated allowed origins for FastAPI (optional; defaults include `http://localhost:3000` and `http://127.0.0.1:3000`)

For the **Next** app, copy `web/.env.example` to `web/.env.local`. Set `INTERNAL_API_URL` to the FastAPI base URL (no trailing slash) and the same `INTERNAL_API_KEY` as on the API when protected; the UI posts to the Next proxy at `/api/analyze`, which forwards to that backend.

### File Limits

- Maximum upload size: 10MB (configurable in `analysis_service.py`: `MAX_UPLOAD_MB`)
- Supported formats: PNG, JPG, JPEG, WEBP (configurable in `analysis_service.py`: `SUPPORTED_EXTS`)

## Project Structure

```
brightr_llm/
├── analysis_service.py   # VLM client + PDF + parsing (Streamlit + API)
├── api_server.py         # FastAPI sessions/reports, GET /health
├── vlm/                  # Moondream2 Flask inference service
│   ├── server.py         # POST /analyze, GET /health
│   └── brightr_vlm_moondream.py
├── app.py                # Streamlit UI
├── web/                  # Next.js (brightr.AI dashboard)
├── requirements.txt
├── .env.example
├── .env                  # Your secrets (not in git)
├── system_prompt         # Customizable AI prompt (optional)
└── reports/              # PDF output (created at runtime)
```

## How It Works

1. **Image Upload**: User uploads an image through Streamlit's file uploader
2. **Image Processing**: Image is validated and converted to RGB format
3. **AI Analysis**: 
   - System prompt is loaded from `system_prompt` file (or uses default)
   - Image and prompt are sent to Google Gemini Vision API
   - Response is parsed to extract structured JSON data
4. **Results Display**: 
   - Summary, findings, and recommendations are displayed in the UI
   - Data is shown in tables for easy reading
5. **PDF Generation**: 
   - ReportLab generates a formatted PDF with all analysis data
   - PDF is saved to `reports/` directory and made available for download

## Dependencies

**Python (API):** `fastapi`, `uvicorn[standard]`, `python-multipart`, `sqlalchemy`, `google-generativeai`, `reportlab`, `Pillow`, `python-dotenv` — see `requirements.txt`

**Python (VLM, `vlm/`):** `torch`, `transformers`, `flask`, `flask-cors`, `pydantic` — see `vlm/requirements.txt` (not in the production image)

**Optional (Streamlit, `app.py`):** install `streamlit` and `pandas` separately if you want the Streamlit UI; they are intentionally **not** in `requirements.txt` or the Docker image.

**Web (`web/`):** `next`, `react`, `tailwindcss` (see `web/package.json`)

## Troubleshooting

### "Missing GEMINI_API_KEY" warning
- Ensure you've created a `.env` file from `.env.example`
- Verify your API key is correctly set in `.env`
- Restart the API after creating/editing `.env`

### "Gemini analysis failed" error
- Check your API key is valid and has sufficient quota
- Verify you have internet connectivity
- Check the model name in `GEMINI_MODEL` environment variable

### VLM (optional, experimental)
- Not required for the default session flow while VLM is commented out in the API
- To experiment: `cd vlm && python server.py`, then re-enable VLM calls in `session_service.py`

### PDF generation fails
- Ensure write permissions for the `reports/` directory
- Check available disk space

### Image upload issues
- Verify file format is supported (PNG, JPG, JPEG, WEBP)
- Check file size is under 10MB
- Ensure the image file is not corrupted

## License

This project is provided as-is for educational and development purposes.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the error messages in the Streamlit UI
3. Check the "Raw model output (debug)" expander if analysis fails
