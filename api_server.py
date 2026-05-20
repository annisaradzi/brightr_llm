"""
FastAPI service for the brightr.AI image analysis pipeline.
Run: uvicorn api_server:app --reload --port 8000
"""

import base64
import hmac
import io
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image
from sqlalchemy.orm import Session

from analysis_service import (
    MAX_UPLOAD_MB,
    SUPPORTED_EXTS,
    AnalysisResult,
    _bytes_len_mb,
    _now_utc,
    analyze_image_with_gemini,
    create_pdf_report,
)
from database import SessionLocal, init_db
from schemas import (
    CreateSessionRequest,
    InspectionItemOut,
    InspectionItemPatch,
    InspectionSessionOut,
    BulkDeleteReportsRequest,
    BulkDeleteReportsResponse,
    DeleteReportOut,
    ReportActionOut,
    ReportDetailOut,
    ReportListResponse,
    RequestChangesBody,
    SubmitSessionRequest,
    UploadImagesResponse,
)
import session_service as svc
import storage

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="brightr_llm", version="1.1.0", lifespan=lifespan)

_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _require_internal_key(request: Request) -> None:
    expected = os.getenv("INTERNAL_API_KEY", "").strip()
    if not expected:
        return
    got = (request.headers.get("X-Internal-Key") or "").strip()
    if not got or not hmac.compare_digest(got, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _detections_for_json(analysis: AnalysisResult) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for d in analysis.detections:
        item: Dict[str, Any] = {"label": d.label, "box": d.box}
        if d.confidence is not None:
            item["confidence"] = d.confidence
        out.append(item)
    return out


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/sessions", response_model=InspectionSessionOut)
def create_session(
    request: Request,
    body: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> InspectionSessionOut:
    _require_internal_key(request)
    created_by = (body.createdBy or request.headers.get("X-User-Email") or "").strip()
    return svc.create_session(db, created_by)


@app.get("/api/sessions/{session_id}", response_model=InspectionSessionOut)
def get_session(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db),
) -> InspectionSessionOut:
    _require_internal_key(request)
    return svc.session_to_out(svc.get_session(db, session_id))


@app.post("/api/sessions/{session_id}/images", response_model=UploadImagesResponse)
async def upload_session_images(
    request: Request,
    session_id: str,
    images: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> UploadImagesResponse:
    _require_internal_key(request)
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")
    items = await svc.upload_images(db, session_id, images)
    return UploadImagesResponse(sessionId=session_id, items=items)


@app.post("/api/sessions/{session_id}/analyze", response_model=InspectionSessionOut)
def analyze_session(
    request: Request,
    session_id: str,
    rerun: bool = False,
    db: Session = Depends(get_db),
) -> InspectionSessionOut:
    _require_internal_key(request)
    return svc.analyze_session(db, session_id, rerun=rerun)


@app.patch(
    "/api/sessions/{session_id}/items/{item_id}",
    response_model=InspectionItemOut,
)
def patch_session_item(
    request: Request,
    session_id: str,
    item_id: str,
    body: InspectionItemPatch,
    db: Session = Depends(get_db),
) -> InspectionItemOut:
    _require_internal_key(request)
    return svc.patch_item(db, session_id, item_id, body)


@app.delete(
    "/api/sessions/{session_id}/items/{item_id}",
    response_model=InspectionSessionOut,
)
def delete_session_item(
    request: Request,
    session_id: str,
    item_id: str,
    db: Session = Depends(get_db),
) -> InspectionSessionOut:
    _require_internal_key(request)
    return svc.delete_item(db, session_id, item_id)


@app.post("/api/sessions/{session_id}/submit", response_model=InspectionSessionOut)
def submit_session(
    request: Request,
    session_id: str,
    body: Optional[SubmitSessionRequest] = None,
    db: Session = Depends(get_db),
) -> InspectionSessionOut:
    _require_internal_key(request)
    return svc.submit_session(db, session_id, body)


@app.get("/api/reports", response_model=ReportListResponse)
def list_reports(
    request: Request,
    q: str = "",
    plant: str = "",
    systemCode: str = "",
    preparer: str = "",
    reviewer: str = "",
    approver: str = "",
    status: str = "",
    page: int = 1,
    limit: int = 25,
    sort: str = "submittedAt:desc",
    db: Session = Depends(get_db),
) -> ReportListResponse:
    _require_internal_key(request)
    return svc.list_reports(
        db,
        q=q,
        plant=plant,
        system_code=systemCode,
        preparer=preparer,
        reviewer=reviewer,
        approver=approver,
        status=status,
        page=page,
        limit=limit,
        sort=sort,
    )


@app.post("/api/reports/bulk-delete", response_model=BulkDeleteReportsResponse)
def bulk_delete_reports(
    request: Request,
    body: BulkDeleteReportsRequest,
    db: Session = Depends(get_db),
) -> BulkDeleteReportsResponse:
    _require_internal_key(request)
    return svc.delete_reports_bulk(db, body.reportIds)


@app.get("/api/reports/{report_id}", response_model=ReportDetailOut)
def get_report_detail(
    request: Request,
    report_id: str,
    db: Session = Depends(get_db),
) -> ReportDetailOut:
    _require_internal_key(request)
    return svc.get_report_detail(db, report_id)


@app.delete("/api/reports/{report_id}", response_model=DeleteReportOut)
def delete_report(
    request: Request,
    report_id: str,
    db: Session = Depends(get_db),
) -> DeleteReportOut:
    _require_internal_key(request)
    return svc.delete_report(db, report_id)


@app.post("/api/reports/{report_id}/approve", response_model=ReportActionOut)
def approve_report(
    request: Request,
    report_id: str,
    db: Session = Depends(get_db),
) -> ReportActionOut:
    _require_internal_key(request)
    return svc.approve_report(db, report_id)


@app.post("/api/reports/{report_id}/request-changes", response_model=ReportActionOut)
def request_report_changes(
    request: Request,
    report_id: str,
    body: RequestChangesBody,
    db: Session = Depends(get_db),
) -> ReportActionOut:
    _require_internal_key(request)
    return svc.request_report_changes(db, report_id, body.comment)


@app.get("/api/reports/{report_id}/pdf")
def download_report_pdf(
    request: Request,
    report_id: str,
    db: Session = Depends(get_db),
):
    _require_internal_key(request)
    path = svc.get_report_pdf_path(db, report_id)
    return FileResponse(path, media_type="application/pdf")


@app.get("/api/sessions/{session_id}/items/{item_id}/image")
def get_item_image(
    request: Request,
    session_id: str,
    item_id: str,
):
    _require_internal_key(request)
    path = storage.load_item_jpeg_path(session_id, item_id)
    if not path:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/api/analyze")
async def api_analyze(
    request: Request,
    image: UploadFile = File(...),
    severity: Optional[str] = Form(None),
) -> dict:
    _require_internal_key(request)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Missing GEMINI_API_KEY. Set it in the environment or `.env`.",
        )

    filename = image.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Supported: {', '.join(SUPPORTED_EXTS)}",
        )

    data = await image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if _bytes_len_mb(data) > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {_bytes_len_mb(data):.1f}MB (max {MAX_UPLOAD_MB}MB)",
        )

    try:
        im = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read image. Use PNG, JPG, or WEBP.")

    try:
        parsed, _ = analyze_image_with_gemini(im, api_key, severity=severity)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    report_id = str(uuid.uuid4())
    generated_at = _now_utc()
    try:
        pdf_bytes = create_pdf_report(
            analysis=parsed,
            report_id=report_id,
            generated_at=generated_at,
            source_filename=filename,
            source_image=im,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}") from e

    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    pdf_name = f"image_analysis_report_{report_id}.pdf"
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")

    w, h = im.size
    return {
        "summary": parsed.summary,
        "findings": parsed.findings,
        "recommendations": parsed.recommendations,
        "detections": _detections_for_json(parsed),
        "reportId": report_id,
        "pdfBase64": pdf_b64,
        "pdfFileName": pdf_name,
        "geminiModel": model_name,
        "imageWidth": w,
        "imageHeight": h,
    }
