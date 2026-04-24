"""
FastAPI service for the brightr.AI image analysis pipeline.
Run: uvicorn api_server:app --reload --port 8000
"""

import base64
import hmac
import io
import os
import uuid
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from analysis_service import (
    MAX_UPLOAD_MB,
    SUPPORTED_EXTS,
    AnalysisResult,
    _bytes_len_mb,
    _now_utc,
    analyze_image_with_gemini,
    create_pdf_report,
)

load_dotenv()

app = FastAPI(title="brightr_llm", version="1.0.0")

_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        item: Dict[str, Any] = {
            "label": d.label,
            "box": d.box,
        }
        if d.confidence is not None:
            item["confidence"] = d.confidence
        out.append(item)
    return out


@app.get("/health")
def health() -> dict:
    return {"ok": True}


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
