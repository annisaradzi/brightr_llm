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

Build in this order. Each component should match the mockup pixel-for-pixel:

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

### Phase 4 — Behavior details (the parts that make UX feel real)

These are not optional — they're why the mockup works:

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

```
GET    /api/inspections/:id
GET    /api/inspections/:id/findings           ?status=&priority=&q=
PATCH  /api/inspections/:id/findings/:fid      partial update, returns full row
POST   /api/inspections/:id/findings           multipart, image upload
DELETE /api/inspections/:id/findings/:fid
POST   /api/inspections/:id/findings/:fid/ai-analyze
POST   /api/inspections/:id/submit
```

PATCH should:
- Accept a partial body (any subset of finding fields)
- Return the **full updated row** so the client can reconcile state
- Compute `editedFields` server-side by diffing changed fields against the
  AI originals — don't trust the client to track this

### Finding fields the frontend expects

The mockup implies this shape. If your backend names things differently,
the frontend can map — but check this list for missing fields:

```ts
{
  id: string
  code: string                    // "IMG-001"
  imageUrl: string
  imageWidth: number
  imageHeight: number

  // AI originals — immutable after first analysis
  aiFindings: string | null
  aiRecommendation: string | null
  aiBoundingBoxes: BBox[] | null  // [{label, x, y, w, h, confidence}]
  aiConfidence: number | null     // 0-1 overall
  aiAnalyzedAt: string | null

  // Engineer-editable
  findings: string | null
  recommendation: string | null
  rustGrade: 'Ri1'|'Ri2'|'R3'|'R4'|'R5' | null
  cof: number | null              // 1-5
  findingsPriority: 'low'|'medium'|'high' | null
  sapPriority: 'low'|'medium'|'high' | null
  equipmentType: '...' | null
  equipmentId: string | null
  recommendationCode: 'TBR'|'TBRy'|'TBP'|'TBM'|'TBS' | null
  furtherInspection: boolean
  openInsulation: boolean
  scaffold: boolean

  // Status
  reviewStatus: 'unreviewed'|'in_progress'|'confirmed'
  editedFields: string[]          // server-computed list of modified field names

  createdAt: string
  updatedAt: string
}
```

### Things to verify on the existing backend

Ask your backend dev or check the code:

1. **PATCH returns the full row?** If it only returns 204, the client has to
   refetch — slower UX. Have it return the updated row.
2. **`updatedAt` returned on every response?** Needed for optimistic locking.
3. **Image upload streams to storage?** If it buffers in memory, large images
   will OOM the server.
4. **AI analysis is async + idempotent?** If it's a synchronous call that
   takes 30s, the frontend has to handle long-polling or websockets.
5. **Concurrency**: can two engineers edit the same finding at once? If yes,
   either last-write-wins with a warning, or use `If-Unmodified-Since` headers.
6. **`editedFields` computed server-side?** If the client computes it, a
   page refresh loses the indicator state.

If any of these are wrong, the frontend can work around it — but the
workarounds are ugly. A 1-line backend change is usually cheaper.

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

## 5. First message to send Cursor

After pasting Section 1 into `.cursorrules` and attaching this brief + the
HTML, your opening chat message:

> Read the implementation brief and the attached HTML mockup. Execute Phase 0
> only — give me the backend discovery report and ask the three confirmation
> questions. Don't write any feature code yet.

That keeps it focused.
