# Cursor Implementation Brief — brightr.AI Frontend

> **Context:** Backend already exists. This brief is for building the frontend
> against it, with the HTML mockup as the UX contract. Backend recommendations
> are in the appendix — read-only suggestions, not required work.

---

## How to use this file

1. Open your project in Cursor.
2. Paste **Section 1** into `.cursorrules` at the project root.
3. Open Cursor chat (Cmd+L), attach `brightr-v2-list-detail.html`, and paste
   **Section 2** as your first message.
4. Cursor will ask the discovery questions in Phase 0 — answer them, then let
   it execute phase-by-phase. Don't skip phases.

---

## 1. SYSTEM PROMPT — paste into `.cursorrules`

```
You are a senior frontend engineer working on brightr.AI, an industrial visual
inspection tool used by piping and equipment engineers in oil & gas plants.

The backend already exists in this repository. Your job is to build the
frontend that matches the attached HTML mockup's UX exactly — keyboard
shortcuts, transitions, edited-field indicators, auto-save behavior, the lot.

Before writing any feature code, you must:
1. Inspect the existing backend routes/handlers/controllers in the repo
2. Read the existing data models / schemas
3. Map what's already implemented vs what the frontend needs
4. Surface gaps to the user — never silently assume a missing endpoint exists

Frontend stack (confirm with user before using):
- React 18 + TypeScript (strict mode)
- Tailwind CSS — extract tokens from the mockup's CSS variables
- shadcn/ui for primitives (Button, Input, Textarea, Select, Toggle, Dialog)
- React Hook Form + Zod for forms and validation
- TanStack Query for server state
- Lucide icons (match the mockup's inline SVGs)

Engineering standards:
- No `any` types. Define interfaces for every data shape from the backend.
- Generate types from the backend if possible (OpenAPI → openapi-typescript,
  GraphQL → graphql-codegen, Prisma → import directly).
- Auto-save with 800ms debounce + visible "saved Xs ago" indicator.
- Optimistic updates for every mutation — this app must feel instant.
- Every interactive element must work with keyboard.
- URL-driven state for selected finding (so refresh + back/forward work).

Domain rules — do not autocomplete these incorrectly:
- Rust grades follow ISO 8501: Ri 1, Ri 2, R3, R4, R5
- Recommendation codes: TBR, TBRy, TBP, TBM, TBS (show full name in dropdowns)
- Priority: low | medium | high
- Equipment types: piping | pressure_vessel | flange | structural | other
- AI status per field: ai_original | ai_edited | engineer_authored
- AI confidence < 60% should trigger a "low confidence" visual warning

When asked to implement a feature:
1. State the plan in 3-5 bullets
2. Identify which backend endpoint(s) you'll call
3. Confirm the response shape matches what you need (read the backend code)
4. Then write the code

Never modify backend files unless the user explicitly asks. If you find a
backend gap, list it for the user and propose either a frontend workaround
or a backend change — let them decide.
```

---

## 2. IMPLEMENTATION BRIEF — paste into Cursor chat with the HTML attached

### Project: brightr.AI frontend

I have a working HTML mockup (attached) and an existing backend in this repo.
Build the frontend against the existing backend. Follow phases in order. Stop
at the end of each phase so I can verify.

### Phase 0 — Discovery (do this first, then stop)

Before writing any feature code, give me a report covering:

1. **Backend stack** — what framework, ORM, auth, where the API routes live
2. **API surface** — list every endpoint relevant to inspections and findings
   (method, path, request shape, response shape). Cite file paths.
3. **Data models** — the existing schema for Inspection and Finding. Note any
   field names that differ from the mockup so we know what to map.
4. **Gaps** — what the mockup needs that the backend doesn't yet provide. For
   each gap, propose either a frontend workaround or a small backend change.
5. **Frontend state** — what's already in the repo (build tooling, existing
   components, routing, state management). I want to know what to reuse.
6. **Type generation** — can we auto-generate types from the backend? (OpenAPI
   spec, GraphQL schema, Prisma client export, tRPC router type, etc.)

After this report, ask me:
- Confirm the frontend framework (React 18 / Next.js / Remix / Vite + React?)
- Confirm any gaps I should patch vs ignore for now
- Confirm the auth/session pattern (cookie, header, anything special)

Then stop. Wait for my answers before Phase 1.

### Phase 1 — Frontend scaffold & design tokens

Once Phase 0 is approved:

1. If a frontend folder doesn't exist, scaffold it (Vite + React + TS is the
   simplest if there's no preference). If one exists, work inside it.
2. Install dependencies as needed: tailwind, shadcn/ui (button, input,
   textarea, select, toggle, dialog, tooltip, sonner), react-hook-form, zod,
   @hookform/resolvers, @tanstack/react-query, lucide-react.
3. Extract every `--var` from the mockup's `:root` block and put them in
   `tailwind.config.ts` as theme tokens. Match exactly — don't invent colors.
4. Load Geist and Geist Mono fonts.
5. Generate types from the backend (use whatever method fits the stack — see
   Phase 0 question 6). Commit the generated file.
6. Set up TanStack Query provider, axios/fetch client with auth, and an
   error boundary at the route level.

Verification: render a blank page using the new tokens (background color,
font) and a single shadcn Button. Show me the page before moving on.

### Phase 2 — API client layer

Create a thin typed API layer in `src/api/`:

```
src/api/
  client.ts              # fetch wrapper with auth, error handling, JSON parsing
  inspections.ts         # getInspection, submitInspection
  findings.ts            # listFindings, getFinding, updateFinding,
                         # createFinding, deleteFinding, runAiAnalysis
  types.ts               # re-export generated types + frontend-only types
```

Each function:
- Returns a Promise of a typed result
- Throws typed errors (4xx → `ApiError`, network → `NetworkError`)
- Has a matching React Query hook in `src/hooks/queries/` and `src/hooks/mutations/`

For mutations, set up:
- `onMutate` for optimistic update
- `onError` for rollback + toast
- `onSettled` to invalidate the right queries

Verification: write a quick test page that lists findings for one inspection
using `useFindings(inspectionId)`. Show me it works before Phase 3.

### Phase 3 — Component build order

You have **four HTML mockups** to implement (all attached):
- `brightr-v2-list-detail.html` — the main analysis screen (new inspection)
- `post-submit-v2.html` — success screen after submitting an inspection
- `reports-list-v2.html` — archive/search view of all submitted reports
- `reports-detail-v2.html` — single report detail view (read-only)

Build in this order. Each component should match the mockup pixel-for-pixel:

#### 3A. Analysis screen (the primary workflow)

1. **`FindingRow`** — the row in the left rail. Props: finding + selected
   state. Renders thumbnail, ID, status dot, summary, priority stripe.
2. **`FindingsRail`** — wraps the row list with header (search, filter pills,
   upload button). Uses `useFindings()` query. Selection via URL param
   `?finding=IMG-001`.
3. **`ImageViewer`** — image + absolutely-positioned bbox overlays from
   the finding's `boundingBoxes` field. Pulse animation on active box.
   Toolbar: zoom, toggle boxes, annotate, download.
4. **`AIConfidencePanel`** — top-N detected conditions with confidence bars,
   color-coded by threshold (>80% green, 60-80% yellow, <60% red).
5. **`FindingsTextarea`** — THE hero component. Build this in isolation on
   a dev-only route `/_dev/textarea` first. Required behavior:
   - Controlled value
   - Char count (current / max)
   - AI badge ("AI confidence: 87%" or "AI-generated")
   - Edited indicator (warning-colored 3px left border) when value differs
     from the AI original
   - Quick-insert chips that append at cursor position (use `selectionStart`,
     not string concat)
   - "Reset to AI" link that restores the original
   - Focus ring matches the mockup's brand-soft glow
6. **`RecommendationField`** — wraps a Select (rec code) + `FindingsTextarea`
7. **`SegmentedPriority`** — accessible radio group as segmented control.
   Color-codes active state (low=green, medium=yellow, high=red).
8. **`ClassificationGrid`** — 2×2 grid of labeled fields (equipment type,
   ID, rust grade, CoF). Pure layout component.
9. **`LogisticsToggles`** — three pill toggles (further insp., open insul.,
   scaffold). Use shadcn Toggle, restyle to match the mockup.
10. **`SaveBar`** — auto-save state indicator + "Mark unreviewed" +
    "Confirm & next" buttons. Reads state from `useAutoSave()`.
11. **`FindingDetail`** — composes everything above into the right panel.
    Reads selected finding from URL, hydrates the form via React Hook Form.

#### 3B. Post-submit success screen

12. **`SubmitSuccessPanel`** — centered card shown after inspection submission.
    Required behavior:
    - Displays inspection ID (system + user report numbers)
    - Shows workflow status: "Awaiting review by [reviewer name]"
    - Primary action: "Back to Reports" (navigates to reports list)
    - Secondary action: "Download PDF"
    - Tertiary links: "View full report", "Edit this report" (only if status = submitted)
    - "Start new analysis" link at bottom

#### 3C. Reports list (archive/search)

13. **`ReportsSearchBar`** — combined search input + filter toggle button.
    Filter panel slides open below when toggled.
14. **`ReportsFilterPanel`** — collapsible 10-field filter grid. Live filtering
    (400ms debounce), no Apply button needed.
15. **`ActiveFilterPills`** — displays active filters as dismissible pills.
    Each pill shows "Field: Value [×]". "Clear all" appears when 2+ active.
16. **`ReportsTable`** — sortable table with status badges, bulk select
    checkboxes. Clicking row opens report detail in new tab.
17. **`BulkActionBar`** — appears when 1+ rows selected. Actions: "Download
    PDFs", "Export CSV", "Clear selection". Shows count: "3 selected".

#### 3D. Report detail (read-only view)

18. **`ReportSummaryCard`** — left column. User report # as H1 (22px bold),
    system report # as secondary (11px mono). Meta list below: plant, system,
    preparer, reviewer, approver, submitted date. Prose executive summary.
19. **`ReportStatsGrid`** — 2×2 grid of big-number stats: total findings,
    high priority count (red), TBS actions (yellow), average CoF.
20. **`ExpandableFindingsTable`** — click row to expand inline, showing full
    findings text + recommendation + image preview. Only one row expanded at
    a time (accordion pattern).
21. **`ApprovalWorkflowBar`** — sticky bottom bar. If status ≠ approved, shows
    "Awaiting review" + two buttons: "Request changes" / "Approve report".
    If approved, shows green success state with approval timestamp.
22. **`ShareDialog`** — modal triggered by "Share" button. Two options:
    "Email PDF to..." (input field + send) or "Copy shareable link" (copy button).

### Phase 4 — Behavior details (the parts that make UX feel real)

These are not optional — they're why the mockup works:

#### Analysis screen behaviors

- **Auto-save**: 800ms debounce. Visible state: `idle → saving → saved at HH:MM`.
  Patches only the changed fields, not the whole form. On error, retry once
  then surface a toast with a "Retry" action.

- **Edited-field detection**: a field is "edited" when its current value
  differs from its AI original. Source of truth: backend response includes
  both `aiFindings` and `findings`. Compute equality on the client, render
  the warning border accordingly. "Reset to AI" copies `aiFindings` →
  `findings` and triggers an immediate save.

- **Quick-insert chips**: clicking a chip inserts the text at the textarea's
  current `selectionStart` position. Preserve surrounding whitespace
  intelligently (don't double-space, don't glue words together).

- **Keyboard navigation**: `j`/`k` and arrow up/down navigate between findings
  in the rail. `Cmd+S` saves immediately. `Cmd+Enter` runs "Confirm & next".
  All shortcuts must check `e.target` and bail out if focus is in an input or
  textarea. Put this logic in `useKeyboardNav()`.

- **URL state**: selected finding is in `?finding=IMG-001`. Browser back,
  forward, and refresh must all land on the same finding. Use the routing
  library's search params API, not local state.

- **Optimistic "Confirm & next"**: clicking immediately advances to the next
  row and updates the current row's status. PATCH fires in the background.
  Roll back on error with a sonner toast.

- **AI re-run conflict handling**: if the engineer has edited a field and
  the user clicks "Re-run AI", do NOT silently overwrite their edit. Show a
  Dialog listing each conflicted field with "keep mine / use new AI" choices.
  This is a trust-critical interaction.

- **Empty / loading / error states** for: no findings yet (upload prompt),
  no AI results yet (greyed bbox area + "Run AI analysis" CTA), image load
  failed (broken-image placeholder + retry).

#### Post-submit success behaviors

- **Auto-redirect after 10 seconds**: if user takes no action, auto-navigate
  to `/reports` after 10s countdown. Show "Redirecting in 5s..." with a
  "Stay here" button to cancel. This prevents the success screen from becoming
  a dead-end.

- **Dynamic workflow message**: "awaiting review by [reviewer name]" should
  pull from the backend's assignment logic. If no reviewer assigned yet,
  show "will be assigned shortly."

- **Conditional "Edit" link**: only show "Edit this report" if backend
  returns `status: 'submitted'`. Once approved, hide this link.

#### Reports list behaviors

- **Filter panel persistence**: collapsed/expanded state in localStorage
  (`reportListFiltersOpen: boolean`). Most users want it collapsed, power
  users want it sticky open.

- **Live filtering with debounce**: 400ms after last keystroke in any filter
  field, fire the query. Show a subtle spinner in the search icon position
  while loading. No separate Apply button.

- **Active filter pills**: extract from URL params on mount. Each pill is
  dismissible (clicking [×] removes that param and refetches). "Clear all"
  removes all params except sort order.

- **URL-driven filter state**: `/reports?plant=MLNG+DUA&status=submitted&sort=submitted:desc`
  Shareable, bookmark-able, back-button safe.

- **Bulk selection state**: persists across pagination but resets on filter
  change (confusing otherwise). "Select all" selects only visible rows, not
  all 1000 in the backend — that's a dangerous footgun.

- **Sortable columns**: clicking toggles asc ↔ desc. Clicking a different
  column resets previous column to neutral. Default sort: `submitted:desc`.
  Sort persists in URL: `?sort=plant:asc`.

- **Empty state**: if filters return zero results, show an empty-state message
  with a "Clear all filters" button. Don't leave them staring at an empty table.

#### Report detail behaviors

- **Expandable finding rows**: only one expanded at a time (accordion). Clicking
  an expanded row collapses it. Clicking a different row collapses the previous
  and expands the new one. No expand-all button — deliberate choice to force
  focus on one finding at a time.

- **Image preview in expanded row**: if image > 200px wide, show zoom cursor
  on hover. Clicking opens full-size lightbox modal with close [×] and
  arrow keys ← → to navigate between findings' images.

- **Share dialog**: two tabs: "Email PDF" (input field for recipient email +
  optional message) and "Get link" (copy-to-clipboard button for shareable URL).
  Shareable URL format: `/reports/:id?share=abc123` where `abc123` is a
  read-only token.

- **Approval workflow**: if `currentUser.role === 'reviewer'` and
  `report.status === 'submitted'`, show the approval bar. "Request changes"
  opens a dialog with a required comment field. "Approve" shows confirmation
  dialog: "This will finalize the report. It cannot be edited after approval."

- **Optimistic approval**: clicking Approve immediately shows green success bar
  "Report approved", hides action buttons, fires PATCH in background. Roll back
  on error.

- **Download PDF**: initiates download immediately (no modal). Show toast:
  "Downloading RF-A1B2C3D4.pdf..."

### Phase 5 — Quality bar

Before declaring anything done:

- `tsc --noEmit` clean, zero `any`
- Every interactive element reachable + operable by keyboard
- Color contrast: WCAG AA. The warning yellow (`#b8860b`) is borderline on
  the soft yellow background — verify with a tool.
- Lighthouse: Performance ≥ 90, Accessibility = 100
- Tests for: auto-save debounce, edited-field detection, keyboard nav, the
  AI conflict dialog
- No console errors or warnings
- Run through the mockup interaction-by-interaction with the keyboard only
  and confirm the production app matches

### Phase 6 — Polish (only after the rest works)

- Page-load skeleton states (rail rows + image viewer skeleton)
- Subtle entrance animation on the rail (staggered, 20ms apart)
- Optimistic image upload with progress
- Bulk select mode (checkbox per rail row, bulk-action bar at the bottom) —
  only if your users actually need it; ask first

---

## 3. APPENDIX — Backend recommendations (optional reading)

Since the backend already exists, these are suggestions to compare against,
not work items. Pick what's useful.

### Endpoints the frontend will hit

**Inspections / Analysis:**
```
POST   /api/inspections                      → create new
GET    /api/inspections/:id                  → load inspection + all findings
PATCH  /api/inspections/:id                  → submit (status → submitted)
GET    /api/inspections/:id/findings         → list findings (paginated)
PATCH  /api/inspections/:id/findings/:fid    → update finding (auto-save)
POST   /api/inspections/:id/findings         → multipart image upload
DELETE /api/inspections/:id/findings/:fid    → delete finding
POST   /api/inspections/:id/findings/:fid/ai-analyze → re-run AI
```

**Reports:**
```
GET    /api/reports                          → list all (query params: plant, status, preparer, etc.)
GET    /api/reports/:id                      → single report detail
GET    /api/reports/:id/pdf                  → download PDF
POST   /api/reports/:id/approve              → approve (status → approved)
POST   /api/reports/:id/request-changes      → send back with comments
POST   /api/reports/bulk/download            → accepts {reportIds: string[]} → ZIP of PDFs
POST   /api/reports/:id/share                → generate shareable read-only token
```

**Critical behaviors:**

PATCH `/api/inspections/:id/findings/:fid` should:
- Accept a partial body (any subset of finding fields)
- Return the **full updated row** so the client can reconcile state
- Compute `editedFields` server-side by diffing changed fields against the
  AI originals — don't trust the client to track this
- If `findings` field is edited and differs from `aiFindings`, append `"findings"`
  to the `editedFields` array (same for `recommendation`, etc.)

GET `/api/reports` should support:
- Query params: `?plant=X&status=Y&preparer=Z&sort=submitted:desc&page=1&limit=50`
- Return: `{reports: Report[], total: number, page: number, limit: number}`
- Default sort: `submitted:desc`
- Default limit: 50

POST `/api/reports/bulk/download` should:
- Stream a ZIP file containing N PDFs
- Filename: `brightr-reports-{timestamp}.zip`
- If >10 reports requested, queue job and return 202 with job ID; send email when ready

### Data models the frontend expects

**Inspection:**
```ts
{
  id: string
  code: string                    // "BR-A1B2C3D4" (system-generated)
  title: string
  status: 'draft' | 'submitted' | 'approved' | 'archived'
  createdById: string
  createdAt: string
  updatedAt: string
  findings: Finding[]             // nested, or fetched separately
}
```

**Finding** (same as before, full shape in the main brief):
```ts
{
  id: string
  code: string                    // "IMG-001"
  imageUrl: string
  imageWidth: number
  imageHeight: number
  
  // AI originals
  aiFindings: string | null
  aiRecommendation: string | null
  aiBoundingBoxes: BBox[] | null
  aiConfidence: number | null
  aiAnalyzedAt: string | null
  
  // Engineer-editable
  findings: string | null
  recommendation: string | null
  rustGrade: 'Ri1'|'Ri2'|'R3'|'R4'|'R5' | null
  cof: number | null
  findingsPriority: 'low'|'medium'|'high' | null
  sapPriority: 'low'|'medium'|'high' | null
  equipmentType: string | null
  equipmentId: string | null
  recommendationCode: 'TBR'|'TBRy'|'TBP'|'TBM'|'TBS' | null
  furtherInspection: boolean
  openInsulation: boolean
  scaffold: boolean
  
  // Status
  reviewStatus: 'unreviewed'|'in_progress'|'confirmed'
  editedFields: string[]
  
  createdAt: string
  updatedAt: string
}
```

**Report** (read-only view of a submitted inspection):
```ts
{
  id: string                      // same as inspection.id
  systemReportNumber: string      // "RF-A1B2C3D4" (generated on submit)
  userReportNumber: string        // "MOD3 CAT1P2 3V-1107" (user-provided or auto-generated)
  
  plant: string
  system: string
  
  preparerId: string
  preparerName: string
  reviewerId: string | null
  reviewerName: string | null
  approverId: string | null
  approverName: string | null
  
  status: 'submitted' | 'in_review' | 'approved'
  submittedAt: string
  reviewedAt: string | null
  approvedAt: string | null
  
  executiveSummary: string        // prose summary, ~200 chars
  
  // Aggregated stats
  totalFindings: number
  highPriorityCount: number
  tbsCount: number                // findings where recommendationCode = TBS
  tbrCount: number
  avgCoF: number
  
  findings: Finding[]             // full array or fetched separately
  
  pdfUrl: string | null           // generated on approval
}
```

### Things to verify on the existing backend

1. **Inspection → Report transformation:** When an inspection is submitted
   (`PATCH /api/inspections/:id` with `{status: 'submitted'}`), does the backend:
   - Generate a `systemReportNumber` (e.g., RF-A1B2C3D4)?
   - Assign a reviewer based on some logic (round-robin, workload, plant)?
   - Create a read-only snapshot or just change the status?

2. **Report filtering performance:** With 10,000+ reports, is there an index on
   `(plant, status, submittedAt)` for fast filtering?

3. **PDF generation:** Is it sync or async? If an inspection has 50 findings with
   images, generating the PDF might take 10-30s. Async + job queue is safer.

4. **Bulk PDF download:** Does a `/bulk/download` endpoint exist? If not, the
   frontend can make N parallel requests and ZIP client-side using JSZip, but
   that's slower and uses more bandwidth.

5. **Approval permissions:** Who can approve? Is it role-based (`user.role === 'approver'`)
   or assignment-based (`user.id === report.approverId`)? Frontend needs to know
   which button to show.

6. **Once approved, truly locked?** Can an admin un-approve and re-open? Or is
   approval a one-way door? Frontend disables "Edit" link accordingly.

If any of these are unclear or missing, flag them in Phase 0 — I'll decide
whether to patch backend or work around in frontend.

---

## 4. Tips for working with Cursor on this

- **Treat the HTML as the spec.** When Cursor's output drifts from the mockup
  (spacing, transitions, hover states), point at specific line numbers in the
  HTML and say "match this exactly."
- **Build the hero textarea standalone first.** Don't try to perfect it inside
  the full form — too many moving parts.
- **Review at phase boundaries.** Run `git diff` after each phase. Cursor's
  small mistakes compound; catching them between phases is cheap.
- **Lock the types first.** Get the generated backend types and the
  finding interface right before building components. Cursor will hallucinate
  field names otherwise.
- **Reject premature abstraction.** Wait for the third use of a pattern
  before extracting it. Three textareas → fine to extract `FormTextarea`.
  Two segments + one toggle → keep them separate.

---

## 5. Application routing structure

The four screens map to these routes:

```
/inspections/new                    → Analysis screen (brightr-v2-list-detail.html)
/inspections/:id/analysis           → Same analysis screen, existing inspection

/inspections/:id/submitted          → Post-submit success (post-submit-v2.html)
                                      Shows after "Submit inspection" button

/reports                            → Reports list (reports-list-v2.html)
/reports/:id                        → Report detail (reports-detail-v2.html)
```

**Flow:**
1. User starts at `/inspections/new`, uploads images, fills findings
2. Clicks "Submit inspection" → PATCH backend, then navigate to `/inspections/:id/submitted`
3. Success screen shows "Back to Reports" → navigate to `/reports`
4. Click a row in reports table → open `/reports/:id` in new tab (target="_blank")
5. In report detail, "Edit this report" → navigate to `/inspections/:id/analysis`

**URL state preservation:**
- `/inspections/:id/analysis?finding=IMG-001` — selected finding persists on refresh
- `/reports?plant=MLNG+DUA&status=submitted` — active filters persist

**Backend endpoints these screens will hit:**

```
POST   /api/inspections                      → create new inspection
GET    /api/inspections/:id                  → load inspection + findings
PATCH  /api/inspections/:id                  → submit inspection (status → submitted)
GET    /api/inspections/:id/findings         → list findings for analysis screen
PATCH  /api/inspections/:id/findings/:fid    → auto-save finding edits

GET    /api/reports                          → list all reports (filterable, sortable)
GET    /api/reports/:id                      → get report detail
GET    /api/reports/:id/pdf                  → download PDF
POST   /api/reports/:id/approve              → approve report (status → approved)
POST   /api/reports/:id/request-changes      → reject with comments
POST   /api/reports/bulk/download            → bulk PDF download (accepts array of IDs)
```

If any of these endpoints don't exist in your backend, flag them in Phase 0.

---

## 6. First message to send Cursor

After pasting Section 1 into `.cursorrules` and attaching this brief + all four
HTML files, your opening chat message:

> I have four HTML mockups (attached) that define the complete inspection workflow:
> analysis screen, post-submit success, reports list, and report detail. Read the
> implementation brief and execute Phase 0 only — give me the backend discovery
> report and ask the three confirmation questions. Don't write any feature code yet.

That keeps it focused.
