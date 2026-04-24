# Deploying `web/` to Vercel

The brightr.AI UI is a Next.js app in this folder. The browser calls same-origin `POST /api/analyze`; that Route Handler proxies to your **public** FastAPI URL using server-only env vars (no `NEXT_PUBLIC_*` for the analyze path).

## 1. Project settings

1. Connect this GitHub repo to [Vercel](https://vercel.com).
2. **Root Directory:** set to `web` (so the build uses `web/package.json`).
3. Framework: Next.js (auto-detected). Build: `npm run build` (default).

## 2. Required environment variables

Set these in the Vercel project (Production; duplicate for **Preview** if you use PR previews, usually pointing at a staging API).

| Variable | Purpose |
|----------|---------|
| `INTERNAL_API_URL` | Public **HTTPS** base URL of FastAPI, **no trailing slash** (e.g. `https://api.example.com`). Required in production builds: if missing or still `localhost`, analyze returns **503**. |
| `INTERNAL_API_KEY` | Shared secret; must **match** `INTERNAL_API_KEY` on the FastAPI host. Sent as `X-Internal-Key` to the API. |
| `AUTH_SECRET` | At least 16 characters; used to sign session JWTs. |
| `AUTH_USERS` | JSON map of email ? password for demo login, e.g. `{"user@company.com":"SecurePassword"}` |

Do **not** set `GEMINI_API_KEY` on Vercel for the Next app; it belongs only on the Python API.

## 3. FastAPI host (separate from Vercel)

Run `api_server.py` on a host with a public URL (Docker on Cloud Run, Fly.io, Render, etc.). Configure there:

- `GEMINI_API_KEY`
- `INTERNAL_API_KEY` (same value as Vercel)
- `CORS_ORIGINS` including your Vercel site origin if you ever call the API from a browser directly (the default flow is server-to-server from the Next Route Handler)

Health check: `GET {INTERNAL_API_URL}/health` ? `{"ok": true}`.

## 4. Limits and plans

- **Function duration:** The analyze Route Handler waits for FastAPI + Gemini. [Vercel Hobby](https://vercel.com/docs/functions/limitations) enforces a short max duration (~10s); slow model calls may **504**. The route sets `maxDuration = 60`; you need a plan that allows that (e.g. Pro) or a different architecture for long runs.
- **Request body size:** Vercel serverless request bodies are typically **~4.5MB**. The Python API may allow up to 10MB; very large images can fail at the Vercel hop first.

## 5. Post-deploy checks

1. Open your Vercel URL, sign in, run an analysis.
2. If you see **503** with a misconfiguration message, fix `INTERNAL_API_URL` in Vercel env and redeploy.
3. If analyze **401**s on the API, align `INTERNAL_API_KEY` on Vercel and FastAPI.
