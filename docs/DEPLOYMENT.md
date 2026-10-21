# Deployment Guide

## Backend → Render

### First-time setup

1. Push your branch to GitHub.
2. In Render: **New → Blueprint**, select this repo. Render reads [`render.yaml`](../render.yaml).
3. On first deploy, Render will prompt for secrets (marked `sync: false`):
   - `GEMINI_API_KEY` — your Google Gemini API key
   - `INTERNAL_API_KEY` — shared secret with the frontend
   - `CORS_ORIGINS` — comma-separated list of allowed frontend origins (e.g. `https://your-app.vercel.app`)
4. Render provisions a persistent disk at `/data` (5GB, per `render.yaml`).
5. On boot, [`start.sh`](../start.sh) checks if `/data/chroma_db` exists:
   - If missing → builds the RAG index from the CSV baked into the Docker image (~2-5 min)
   - If present → skips straight to starting `uvicorn`

### Subsequent deploys

- `autoDeploy: true` in `render.yaml` means pushing to the connected branch triggers an automatic deploy.
- Or trigger manually: Render dashboard → your service → **Manual Deploy**.

### Updating the RAG dataset

If `data/inspection_dataset_with_extracted.csv` changes:
1. Commit the updated CSV (it's tracked in git, not gitignored).
2. Push and deploy — but note `start.sh` **skips rebuilding if `/data/chroma_db` already exists**.
3. To force a rebuild: open a shell in the Render dashboard for your service and run:
   ```bash
   rm -rf /data/chroma_db
   python scripts/build_rag_index.py
   ```
   Then restart the service (or just let the next deploy's `start.sh` rebuild it, since the folder is now gone).

---

## Frontend → Vercel

### Environment variables (Project Settings → Environment Variables)

| Variable | Environment | Value |
|---|---|---|
| `INTERNAL_API_URL` | Production | `https://your-backend.onrender.com` |
| `INTERNAL_API_URL` | Preview | your test backend URL (ngrok or a separate Render service) — **never point Preview at Production's backend if testing risky changes** |
| `INTERNAL_API_KEY` | Production + Preview | matches the Render backend's `INTERNAL_API_KEY` |

**Do not** set `GEMINI_API_KEY` on Vercel — it belongs only on the backend (see [`web/VERCEL.md`](../web/VERCEL.md)).

### Testing changes safely before Production

1. Run your modified backend locally: `uvicorn api_server:app --reload --port 8000 --host 0.0.0.0`
2. Expose it with ngrok: `ngrok http 8000`
3. Set the ngrok HTTPS URL as `INTERNAL_API_URL` for the **Preview** environment only in Vercel.
4. Push a branch — Vercel auto-creates a Preview Deployment using your local backend.
5. Once verified, deploy the backend changes properly to Render, then update Production's `INTERNAL_API_URL` if needed (it usually doesn't change — only Preview does, for local testing).

---

## Common Deployment Issues

| Symptom | Cause | Fix |
|---|---|---|
| `Server misconfiguration: set INTERNAL_API_URL` | Env var missing/empty on Vercel | Add it in Project Settings → Environment Variables, redeploy |
| Render build succeeds but boot hangs | RAG index building on every boot | Confirm `/data/chroma_db` persists between deploys (check disk is actually mounted) |
| `429` or `400` from Gemini | Invalid/missing API key, or quota exceeded | Verify `GEMINI_API_KEY` in Render env vars, check Google Cloud billing/quota |
| CORS errors in browser console | `CORS_ORIGINS` doesn't include the Vercel domain | Update `CORS_ORIGINS` env var on Render to include your exact Vercel URL |
