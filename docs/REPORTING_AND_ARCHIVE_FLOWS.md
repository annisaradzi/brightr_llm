# Reporting and Archive Flows

This document describes how an inspection session moves from `draft` to an
archived, reviewable, downloadable **report**, and what files / DB rows / API
calls are involved at each step.

Status terms used throughout:

| Status       | Meaning                                                         |
|--------------|-----------------------------------------------------------------|
| `draft`      | Working session — uploads, analysis, edits allowed              |
| `submitted`  | Locked. PDF + sidecar files written. Appears in the report list |
| `in_review`  | Same as `submitted` for visibility; awaiting approval           |
| `approved`   | Terminal state                                                  |

The status set considered "report" (i.e. archived and listable) is defined in
`session_service.py` as:

```35:35:session_service.py
REPORT_STATUSES = frozenset({"submitted", "in_review", "approved"})
```

---

## 1. Storage layout (the on-disk archive)

All binary artifacts for a session live under `storage/sessions/<sessionId>/`
(configurable via `STORAGE_ROOT`). Layout:

```
storage/
└── sessions/
    └── {sessionId}/
        ├── {itemId}.jpg              # Original upload, normalized to JPEG q=90
        ├── {itemId}_findings.txt     # Findings + recommendation sidecar (post-submit)
        ├── {itemId}_bboxes.json      # AI bounding boxes sidecar (post-submit)
        ├── manifest.json             # Per-session manifest (post-submit)
        └── executive_report.pdf      # Generated executive PDF (post-submit)
```

JPEGs are written on upload; the four other files are written **only on
submit**.

The helpers that own this directory are in `storage.py`:

```13:22:storage.py
def session_dir(session_id: str) -> Path:
    p = STORAGE_ROOT / "sessions" / session_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_item_jpeg(session_id: str, item_id: str, image: Image.Image) -> str:
    out = session_dir(session_id) / f"{item_id}.jpg"
    image.convert("RGB").save(out, format="JPEG", quality=90)
    return f"storage/sessions/{session_id}/{item_id}.jpg"
```

The DB stores structured data + relative paths; the filesystem stores the
actual blobs. The DB column `inspection_sessions.pdf_path` only becomes
non-null after a successful submit.

---

## 2. From `draft` to `submitted` — the submit flow

Entry point: `POST /api/sessions/{id}/submit` (`api_server.py`) →
`session_service.submit_session()`.

### 2.1 Preconditions

- Session must exist.
- Must have at least one `InspectionItem` (else `400 No items to submit`).
- If already `submitted`, the call is idempotent and returns the existing
  session (no rewrites).

### 2.2 What submit does, in order

1. **Merge optional metadata** from `SubmitSessionRequest`
   (`userReportNumber`, `plant`, `systemCode`, `preparerName`, `reviewerName`,
   `approverName`). Empty strings → `None`.
2. **Assign the system report number** (`RF-XXXXXXXX`, deterministic from
   the session UUID) via `_system_report_number()`.
3. **Default preparer** to `created_by` if not provided.
4. **Default executive summary** if blank, via `_default_summary()`:
   total findings, high-priority count, and the primary finding label.
5. **For every item**: parse `ai_bounding_boxes_json` and write per-item
   sidecars:

   ```39:51:storage.py
   def write_item_sidecars(
       session_id: str,
       item_id: str,
       findings_text: str,
       recommendation_text: str,
       bboxes: List[Dict[str, Any]],
   ) -> None:
       base = session_dir(session_id)
       (base / f"{item_id}_findings.txt").write_text(
           f"FINDINGS\n{findings_text}\n\nRECOMMENDATION\n{recommendation_text}\n",
           encoding="utf-8",
       )
       (base / f"{item_id}_bboxes.json").write_text(json.dumps(bboxes, indent=2), encoding="utf-8")
   ```

6. **Render `executive_report.pdf`** via ReportLab (`_write_report_pdf()`):
   header block (system #, user #, plant/system, preparer/reviewer/approver),
   executive summary, and a `Findings` list with `code | equipmentId |
   priority | recommendationCode`. PDF goes to
   `storage/sessions/<sid>/executive_report.pdf`.
7. **Set `pdf_path`** on the session to the relative path.
8. **Write `manifest.json`** describing the archive layout for downstream
   consumers (SAP integration, exports, etc.):

   ```25:36:storage.py
   def write_submit_artifacts(
       session_id: str,
       manifest_items: List[Dict[str, Any]],
       metadata: Optional[Dict[str, Any]] = None,
   ) -> Path:
       base = session_dir(session_id)
       manifest_path = base / "manifest.json"
       manifest = {"sessionId": session_id, "items": manifest_items}
       if metadata:
           manifest["report"] = metadata
       manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
       return manifest_path
   ```

9. **Verify PDF exists** — if not, `500 Failed to generate report PDF` and
   the DB transaction rolls back (no half-submit).
10. **Flip status** to `submitted` and stamp `submitted_at = now(UTC)`.

After this call returns, the session is **immutable** to all editing
endpoints (uploads / analyze / patch all return `400` once `status ==
"submitted"`).

---

## 3. The report list (archive index)

Entry point: `GET /api/reports` → `session_service.list_reports()`.

Only sessions whose status is in `REPORT_STATUSES` are visible. Everything
in `draft` is hidden from the archive.

### 3.1 Query parameters

| Param        | Behavior                                                     |
|--------------|--------------------------------------------------------------|
| `q`          | Case-insensitive substring over system#, user#, plant, system code, preparer |
| `plant`      | Substring match (case-insensitive)                           |
| `systemCode` | Substring match                                              |
| `preparer`   | Substring match on `preparer_name` or fallback `created_by`  |
| `reviewer`   | Substring match on `reviewer_name`                           |
| `approver`   | Substring match on `approver_name`                           |
| `status`     | Exact match: `submitted` / `in_review` / `approved`          |
| `page`       | 1-based (clamped ≥ 1)                                        |
| `limit`      | Page size (clamped to `[1, 100]`)                            |
| `sort`       | `field:dir` — `submittedAt` (default), `createdAt`, `plant`, `systemCode`; dir `asc`/`desc` |

### 3.2 Per-row aggregates

Each row is built by `_report_summary_row()` and includes:

- `totalFindings` — `len(items)`
- `highPriorityCount` — items where `findings_priority == "high"`
- `tbsCount` — items with `recommendation_code == "TBS"`
- `avgCof` — mean of non-null `cof` values, rounded to 2 dp
- `equipmentType` / `equipmentId` from the **primary item** (highest
  priority, then highest CoF, then lowest sort order — see `_pick_primary_item`)

### 3.3 Implementation notes

The filter is currently done **in Python after a `db.query(...).all()`**, not
in SQL. Fine for small archives but should be revisited if the table grows
(see `list_reports` in `session_service.py`).

---

## 4. Report detail

Entry point: `GET /api/reports/{id}` → `session_service.get_report_detail()`.

- Reuses `_report_summary_row()` for aggregates.
- Returns `executiveSummary` (falls back to `_default_summary()` if the row
  field is empty).
- Includes the full `items[]` array with bounding boxes, AI fields, edited
  fields diff, etc. — same shape as the inspection session output.
- `pdfUrl` is populated only if `pdf_path` is set (i.e. a real submit
  happened).
- 404 if the session exists but its status is not in `REPORT_STATUSES`.

---

## 5. Approval and "request changes" flow

```
                  approve
   submitted ───────────────► approved
       ▲                          │
       │     request_changes      │
       └──────────────────────────┘
            (also from in_review)
```

### 5.1 `POST /api/reports/{id}/approve`

`approve_report()`:

- Allowed from `submitted` or `in_review`.
- Sets `status = "approved"`, stamps `approved_at`, bumps `updated_at`.
- Returns `ReportActionOut { id, status, message }`.

### 5.2 `POST /api/reports/{id}/request-changes`

Body: `{ "comment": "<non-empty>" }` (validated by `RequestChangesBody`).

`request_report_changes()`:

- Allowed from `submitted`, `in_review`, or `approved` (so an approval can
  be revoked).
- Forces status back to `submitted`.
- Writes `review_comment`, stamps `reviewed_at`, clears `approved_at`.

> Note: there is no explicit "set to `in_review`" endpoint right now —
> `submitted` and `in_review` are mostly equivalent for visibility, and the
> approve/request-changes pair drives the transitions.

---

## 6. PDF download (the binary archive)

Entry point: `GET /api/reports/{id}/pdf` → `session_service.get_report_pdf_path()`.

Guards:

1. Status must be in `REPORT_STATUSES`.
2. `pdf_path` must be non-null on the DB row.
3. The PDF file must actually exist on disk at
   `storage/sessions/<sid>/executive_report.pdf`.

If any check fails → `404 Report PDF not found`. On success, FastAPI streams
the file with `media_type="application/pdf"` via `FileResponse`.

---

## 7. Image serving (per-item asset)

Entry point: `GET /api/sessions/{sessionId}/items/{itemId}/image` →
`storage.load_item_jpeg_path()`.

This works regardless of session status (drafts and submitted reports both
serve images), so the report detail page can keep rendering thumbnails and
overlays after the session is locked.

---

## 8. BFF / authentication layer

All `/api/sessions/*` and `/api/reports/*` calls are protected by:

- Optional `INTERNAL_API_KEY` — when set, the FastAPI side requires the
  `X-Internal-Key` header (constant-time compared in `_require_internal_key`
  in `api_server.py`).
- The Next.js BFF (`web/src/lib/internal-api.ts`) injects this header
  server-side so the browser never sees it.
- The Next middleware (`web/src/middleware.ts`) gates `/` and `/reports/*`
  behind the `brightr_session` JWT cookie.

The web client surfaces for reports already exist in
`web/src/api/reports.ts` (`listReports`, `getReport`, `approveReport`,
`requestReportChanges`, `reportPdfUrl`), but per the repo summary the
matching Next.js BFF routes and pages under `web/src/app/reports/*` are not
wired yet — the FastAPI side is the source of truth.

---

## 9. End-to-end summary diagram

```
                ┌─────────┐  POST /api/sessions
                │ draft   │◄────────────────────────────
                └────┬────┘                              
                     │ POST /images (multipart)          
                     │ POST /analyze        (VLM call)   
                     │ PATCH /items/{itemId}             
                     ▼                                    
              POST /sessions/{id}/submit
                     │
                     │ writes per-item findings.txt + bboxes.json
                     │ renders executive_report.pdf
                     │ writes manifest.json
                     │ sets pdf_path
                     ▼
                ┌───────────┐
                │ submitted │ ── GET /api/reports (list)
                │           │ ── GET /api/reports/{id} (detail)
                │           │ ── GET /api/reports/{id}/pdf
                └────┬──────┘
                     │ POST /approve            POST /request-changes
                     ▼                          (from any of submitted /
                ┌───────────┐                    in_review / approved,
                │ approved  │◄─── request_changes  forces back to submitted)
                └───────────┘
```

---

## 10. Files involved (quick index)

| Concern                          | File                                  |
|----------------------------------|---------------------------------------|
| HTTP surface                     | `api_server.py`                       |
| Submit + report business logic   | `session_service.py`                  |
| ORM models                       | `models.py`                           |
| Request/response DTOs            | `schemas.py`                          |
| On-disk archive helpers          | `storage.py`                          |
| API contract reference           | `docs/PHASE1_API_CONTRACT.md`         |
| High-level architecture overview | `docs/REPO_SUMMARY.md`                |
| Next.js report API client        | `web/src/api/reports.ts`              |
| Next.js auth gate                | `web/src/middleware.ts`               |
| Next.js BFF proxy helper         | `web/src/lib/internal-api.ts`         |
