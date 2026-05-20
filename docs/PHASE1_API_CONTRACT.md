# Phase 1 API Contract (frozen)

Base URL (FastAPI): `http://127.0.0.1:8000`  
BFF (Next.js): `/api/sessions/*` proxies with cookie auth + `X-Internal-Key`.

## Enums

- `rustGrade`: `Ri1` | `Ri2` | `R3` | `R4` | `R5`
- `recommendationCode`: `TBR` | `TBRy` | `TBP` | `TBM` | `TBS`
- `findingsPriority` / `sapPriority`: `low` | `medium` | `high`
- `equipmentType`: `piping` | `pressure_vessel` | `flange` | `structural` | `other`
- `reviewStatus`: `unreviewed` | `in_progress` | `confirmed`
- `sessionStatus`: `draft` | `submitted`
- `analysisStatus`: `pending` | `complete` | `failed`

## POST /api/sessions

Request: `{ "createdBy": "engineer@example.com" }` (optional; BFF sets from session)

Response `201`:
```json
{
  "id": "uuid",
  "status": "draft",
  "createdBy": "engineer@example.com",
  "createdAt": "2026-05-16T00:00:00Z",
  "submittedAt": null,
  "items": []
}
```

## POST /api/sessions/{id}/images

Multipart: `images` (one or more files)

Response `200`:
```json
{
  "sessionId": "uuid",
  "items": [ { "...InspectionItem..." } ]
}
```

## POST /api/sessions/{id}/analyze

Query: `rerun=false` (if true, re-analyze completed items)

Response `200`: full session with updated items

## GET /api/sessions/{id}

Response `200`: session + `items[]`

## PATCH /api/sessions/{id}/items/{itemId}

Partial body (any subset):
```json
{
  "findings": "string",
  "recommendation": "string",
  "rustGrade": "R4",
  "cof": 3,
  "findingsPriority": "medium",
  "sapPriority": "high",
  "equipmentType": "piping",
  "equipmentId": "EQ-001",
  "recommendationCode": "TBR",
  "furtherInspection": true,
  "openInsulation": false,
  "scaffold": false,
  "reviewStatus": "in_progress"
}
```

Response `200`: full updated `InspectionItem` with `editedFields[]`

## POST /api/sessions/{id}/submit

Response `200`: session with `status: "submitted"` and export paths in manifest

## InspectionItem shape

```json
{
  "id": "uuid",
  "code": "IMG-001",
  "sessionId": "uuid",
  "sortOrder": 0,
  "imageUrl": "/api/sessions/{sessionId}/items/{id}/image",
  "imageWidth": 1920,
  "imageHeight": 1080,
  "aiFindings": "string | null",
  "aiRecommendation": "string | null",
  "aiBoundingBoxes": [],
  "aiConfidence": 0.87,
  "aiAnalyzedAt": "ISO8601 | null",
  "findings": "string | null",
  "recommendation": "string | null",
  "rustGrade": "R4",
  "cof": 3,
  "findingsPriority": "medium",
  "sapPriority": "high",
  "equipmentType": "piping",
  "equipmentId": "EQ-A1B2-001",
  "recommendationCode": "TBR",
  "furtherInspection": false,
  "openInsulation": false,
  "scaffold": false,
  "reviewStatus": "unreviewed",
  "analysisStatus": "complete",
  "analysisError": null,
  "editedFields": ["findings"],
  "createdAt": "ISO8601",
  "updatedAt": "ISO8601"
}
```
