"""Business logic for inspection sessions and findings items."""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from analysis_service import (
    MAX_UPLOAD_MB,
    SUPPORTED_EXTS,
    _bytes_len_mb,
    analyze_image_structured_with_gemini,
    brand_logo_flowable,
    # analyze_image_with_vlm,  # VLM disabled temporarily
    structured_result_to_item_fields,
)
from models import InspectionItem, InspectionSession
from schemas import (
    BoundingBoxOut,
    InspectionItemOut,
    InspectionItemPatch,
    InspectionSessionOut,
    BulkDeleteFailedItem,
    BulkDeleteReportsResponse,
    DeleteReportOut,
    ReportActionOut,
    ReportDetailOut,
    ReportListResponse,
    ReportSummaryOut,
    SubmitSessionRequest,
)

REPORT_STATUSES = frozenset({"submitted", "in_review", "approved"})
import storage

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _item_image_url(session_id: str, item_id: str) -> str:
    return f"/api/sessions/{session_id}/items/{item_id}/image"


def _report_pdf_url(session_id: str) -> str:
    return f"/api/reports/{session_id}/pdf"


def _system_report_number(session: InspectionSession) -> str:
    if session.system_report_number:
        return session.system_report_number
    short = session.id.replace("-", "").upper()[:8]
    return f"RF-{short}"


def _pick_primary_item(items: List[InspectionItem]) -> Optional[InspectionItem]:
    if not items:
        return None
    priority_order = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        items,
        key=lambda i: (
            priority_order.get((i.findings_priority or "").lower(), 9),
            -(i.cof or 0),
            i.sort_order,
        ),
    )[0]


def _parse_bboxes_json(raw: Optional[str]) -> List[Dict[str, Any]]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _get_ai_snapshot(item: InspectionItem) -> Dict[str, Any]:
    if not item.ai_raw_json:
        return {}
    try:
        data = json.loads(item.ai_raw_json)
        snap = data.get("aiSnapshot")
        return snap if isinstance(snap, dict) else {}
    except json.JSONDecodeError:
        return {}


def compute_edited_fields(item: InspectionItem) -> List[str]:
    snap = _get_ai_snapshot(item)
    if not snap:
        return []
    edited: List[str] = []
    mapping = {
        "findings": item.findings,
        "recommendation": item.recommendation,
        "rustGrade": item.rust_grade,
        "cof": item.cof,
        "findingsPriority": item.findings_priority,
        "sapPriority": item.sap_priority,
        "equipmentType": item.equipment_type,
        "equipmentId": item.equipment_id,
        "recommendationCode": item.recommendation_code,
        "furtherInspection": item.further_inspection,
        "openInsulation": item.open_insulation,
        "scaffold": item.scaffold,
    }
    for api_key, current in mapping.items():
        if api_key not in snap:
            continue
        ai_val = snap[api_key]
        if current != ai_val:
            edited.append(api_key)
    return edited


def item_to_out(item: InspectionItem) -> InspectionItemOut:
    boxes = _parse_bboxes_json(item.ai_bounding_boxes_json)
    out_boxes = []
    for b in boxes:
        box = b.get("box") or b
        out_boxes.append(
            {
                "label": b.get("label", ""),
                "x": box.get("x", 0),
                "y": box.get("y", 0),
                "w": box.get("width", box.get("w", 0)),
                "h": box.get("height", box.get("h", 0)),
                "confidence": b.get("confidence"),
            }
        )
    return InspectionItemOut(
        id=item.id,
        code=item.code,
        sessionId=item.session_id,
        sortOrder=item.sort_order,
        imageUrl=_item_image_url(item.session_id, item.id),
        imageWidth=item.image_width,
        imageHeight=item.image_height,
        aiFindings=item.ai_findings,
        aiRecommendation=item.ai_recommendation,
        aiBoundingBoxes=[BoundingBoxOut(**b) for b in out_boxes],
        aiConfidence=item.ai_confidence,
        aiAnalyzedAt=item.ai_analyzed_at,
        findings=item.findings,
        recommendation=item.recommendation,
        rustGrade=item.rust_grade,
        cof=item.cof,
        findingsPriority=item.findings_priority,
        sapPriority=item.sap_priority,
        equipmentType=item.equipment_type,
        equipmentId=item.equipment_id,
        recommendationCode=item.recommendation_code,
        furtherInspection=item.further_inspection,
        openInsulation=item.open_insulation,
        scaffold=item.scaffold,
        reviewStatus=item.review_status,
        analysisStatus=item.analysis_status,
        analysisError=item.analysis_error,
        editedFields=compute_edited_fields(item),
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


def session_to_out(session: InspectionSession) -> InspectionSessionOut:
    return InspectionSessionOut(
        id=session.id,
        status=session.status,
        createdBy=session.created_by,
        systemReportNumber=session.system_report_number,
        userReportNumber=session.user_report_number,
        plant=session.plant,
        systemCode=session.system_code,
        preparerName=session.preparer_name,
        reviewerName=session.reviewer_name,
        approverName=session.approver_name,
        executiveSummary=session.executive_summary,
        pdfUrl=_report_pdf_url(session.id) if session.pdf_path else None,
        createdAt=session.created_at,
        updatedAt=session.updated_at or session.created_at,
        submittedAt=session.submitted_at,
        items=[item_to_out(i) for i in session.items],
    )


def create_session(db: Session, created_by: str) -> InspectionSessionOut:
    row = InspectionSession(created_by=created_by or "")
    db.add(row)
    db.flush()
    return session_to_out(row)


def get_session(db: Session, session_id: str) -> InspectionSession:
    row = db.get(InspectionSession, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


def _validate_ext(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Supported: {', '.join(SUPPORTED_EXTS)}",
        )
    return ext


async def upload_images(
    db: Session,
    session_id: str,
    files: List[UploadFile],
) -> List[InspectionItemOut]:
    session = get_session(db, session_id)
    if session.status == "submitted":
        raise HTTPException(status_code=400, detail="Cannot upload to a submitted session")

    existing = len(session.items)
    out_items: List[InspectionItemOut] = []
    for idx, upload in enumerate(files):
        filename = upload.filename or "upload"
        _validate_ext(filename)
        data = await upload.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty file")
        if _bytes_len_mb(data) > MAX_UPLOAD_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File too large (max {MAX_UPLOAD_MB}MB)",
            )
        try:
            import io

            im = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read image")

        item_id = str(uuid.uuid4())
        sort_order = existing + idx
        code = f"IMG-{sort_order + 1:03d}"
        short = session_id.replace("-", "")[:8].upper()
        equipment_id = f"EQ-{short}-{sort_order + 1:03d}"

        item = InspectionItem(
            id=item_id,
            session_id=session_id,
            sort_order=sort_order,
            code=code,
            image_path=storage.save_item_jpeg(session_id, item_id, im),
            image_width=im.size[0],
            image_height=im.size[1],
            equipment_id=equipment_id,
            analysis_status="pending",
        )
        db.add(item)
        db.flush()
        out_items.append(item_to_out(item))
    return out_items


def _apply_structured_to_item(item: InspectionItem, fields: Dict[str, Any], raw: str) -> None:
    item.ai_findings = fields.get("aiFindings")
    item.ai_recommendation = fields.get("aiRecommendation")
    item.findings = fields.get("findings")
    item.recommendation = fields.get("recommendation")
    item.rust_grade = fields.get("rustGrade")
    item.cof = fields.get("cof")
    item.findings_priority = fields.get("findingsPriority")
    item.sap_priority = fields.get("sapPriority")
    item.equipment_type = fields.get("equipmentType")
    if fields.get("equipmentId"):
        item.equipment_id = fields.get("equipmentId")
    item.recommendation_code = fields.get("recommendationCode")
    item.further_inspection = bool(fields.get("furtherInspection", False))
    item.open_insulation = bool(fields.get("openInsulation", False))
    item.scaffold = bool(fields.get("scaffold", False))
    item.ai_confidence = fields.get("aiConfidence")
    item.ai_bounding_boxes_json = json.dumps(fields.get("aiBoundingBoxes") or [])
    item.ai_analyzed_at = _utcnow()
    item.analysis_status = "complete"
    item.analysis_error = None
    snap = {
        "findings": item.findings,
        "recommendation": item.recommendation,
        "rustGrade": item.rust_grade,
        "cof": item.cof,
        "findingsPriority": item.findings_priority,
        "sapPriority": item.sap_priority,
        "equipmentType": item.equipment_type,
        "equipmentId": item.equipment_id,
        "recommendationCode": item.recommendation_code,
        "furtherInspection": item.further_inspection,
        "openInsulation": item.open_insulation,
        "scaffold": item.scaffold,
    }
    item.ai_raw_json = json.dumps({"raw": raw, "aiSnapshot": snap})


def analyze_session(db: Session, session_id: str, rerun: bool = False) -> InspectionSessionOut:
    session = get_session(db, session_id)
    if session.status == "submitted":
        raise HTTPException(status_code=400, detail="Cannot analyze a submitted session")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="Missing GEMINI_API_KEY")
    # vlm_url = os.getenv("VLM_ENDPOINT_URL", "http://localhost:5001").strip()
    # if not vlm_url:
    #     raise HTTPException(status_code=503, detail="Missing VLM_ENDPOINT_URL")

    for item in session.items:
        if item.analysis_status == "complete" and not rerun:
            continue
        path = storage.load_item_jpeg_path(session_id, item.id)
        if not path:
            item.analysis_status = "failed"
            item.analysis_error = "Image file missing"
            continue
        try:
            im = Image.open(path).convert("RGB")
            structured, raw = analyze_image_structured_with_gemini(im, api_key)
            # structured, raw = analyze_image_with_vlm(path, item.id, vlm_url)
            fields = structured_result_to_item_fields(structured)
            _apply_structured_to_item(item, fields, raw)
        except Exception as e:
            item.analysis_status = "failed"
            item.analysis_error = str(e)
        item.updated_at = _utcnow()

    db.flush()
    return session_to_out(session)


def patch_item(
    db: Session,
    session_id: str,
    item_id: str,
    patch: InspectionItemPatch,
) -> InspectionItemOut:
    session = get_session(db, session_id)
    if session.status == "submitted":
        raise HTTPException(status_code=400, detail="Session is submitted and immutable")

    item = next((i for i in session.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    data = patch.model_dump(exclude_unset=True)
    field_map = {
        "findings": "findings",
        "recommendation": "recommendation",
        "rustGrade": "rust_grade",
        "cof": "cof",
        "findingsPriority": "findings_priority",
        "sapPriority": "sap_priority",
        "equipmentType": "equipment_type",
        "equipmentId": "equipment_id",
        "recommendationCode": "recommendation_code",
        "furtherInspection": "further_inspection",
        "openInsulation": "open_insulation",
        "scaffold": "scaffold",
        "reviewStatus": "review_status",
    }
    for api_key, col in field_map.items():
        if api_key in data:
            setattr(item, col, data[api_key])
    item.updated_at = _utcnow()
    db.flush()
    return item_to_out(item)


def delete_item(db: Session, session_id: str, item_id: str) -> InspectionSessionOut:
    session = get_session(db, session_id)
    if session.status == "submitted":
        raise HTTPException(status_code=400, detail="Session is submitted and immutable")

    item = next((i for i in session.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if item.analysis_status == "complete":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete an analyzed finding; only pending or failed uploads can be removed",
        )

    storage.delete_item_artifacts(session_id, item_id)
    db.delete(item)
    session.updated_at = _utcnow()
    db.flush()
    db.refresh(session)
    return session_to_out(session)


def _report_summary_row(session: InspectionSession) -> ReportSummaryOut:
    total = len(session.items)
    high_count = sum(1 for i in session.items if (i.findings_priority or "").lower() == "high")
    tbs_count = sum(1 for i in session.items if (i.recommendation_code or "") == "TBS")
    cofs = [i.cof for i in session.items if i.cof is not None]
    avg_cof = round(sum(cofs) / len(cofs), 2) if cofs else None
    primary = _pick_primary_item(session.items)

    return ReportSummaryOut(
        id=session.id,
        systemReportNumber=_system_report_number(session),
        userReportNumber=session.user_report_number,
        plant=session.plant,
        systemCode=session.system_code,
        preparerName=session.preparer_name,
        reviewerName=session.reviewer_name,
        approverName=session.approver_name,
        equipmentType=primary.equipment_type if primary else None,
        equipmentId=primary.equipment_id if primary else None,
        status=session.status,
        submittedAt=session.submitted_at,
        totalFindings=total,
        highPriorityCount=high_count,
        tbsCount=tbs_count,
        avgCof=avg_cof,
    )


def _default_summary(session: InspectionSession) -> str:
    total = len(session.items)
    high_count = sum(1 for i in session.items if (i.findings_priority or "").lower() == "high")
    primary = _pick_primary_item(session.items)
    primary_label = (primary.findings or primary.ai_findings or "inspection finding").strip()
    primary_label = primary_label[:120]
    return (
        f"{total} findings recorded. "
        f"{high_count} high-priority findings require attention. "
        f"Primary observation: {primary_label}."
    )


def _report_pdf_abs_path(session_id: str) -> str:
    return str(storage.session_dir(session_id) / "executive_report.pdf")


def _fmt_dt(dt) -> str:
    if not dt:
        return "-"
    try:
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return str(dt)


def _write_report_pdf(session: InspectionSession) -> str:
    path = _report_pdf_abs_path(session.id)

    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title="Brightr.AI Executive Inspection Report",
        author="Brightr.AI",
    )

    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=base_styles["Title"],
        fontSize=18,
        spaceBefore=4,
        spaceAfter=10,
        alignment=0,
    )
    h_style = ParagraphStyle(
        "ReportH2",
        parent=base_styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=4,
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=base_styles["BodyText"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#57544D"),
    )
    meta_value = ParagraphStyle(
        "MetaValue",
        parent=base_styles["BodyText"],
        fontSize=9.5,
        leading=12,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=base_styles["BodyText"],
        fontSize=10,
        leading=13,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=base_styles["BodyText"],
        fontSize=8.5,
        leading=11,
        wordWrap="CJK",
    )
    cell_center = ParagraphStyle(
        "TableCellCenter",
        parent=cell_style,
        alignment=1,
    )

    story: List[Any] = []
    story.append(brand_logo_flowable(1.65 * inch))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Executive Inspection Report", title_style))

    meta_rows = [
        [Paragraph("System report #", meta_label),
         Paragraph(_system_report_number(session), meta_value),
         Paragraph("Submitted", meta_label),
         Paragraph(_fmt_dt(session.submitted_at), meta_value)],
        [Paragraph("User report #", meta_label),
         Paragraph(session.user_report_number or "-", meta_value),
         Paragraph("Status", meta_label),
         Paragraph((session.status or "-").replace("_", " ").title(), meta_value)],
        [Paragraph("Plant", meta_label),
         Paragraph(session.plant or "-", meta_value),
         Paragraph("System", meta_label),
         Paragraph(session.system_code or "-", meta_value)],
        [Paragraph("Preparer", meta_label),
         Paragraph(session.preparer_name or session.created_by or "-", meta_value),
         Paragraph("Reviewer", meta_label),
         Paragraph(session.reviewer_name or "-", meta_value)],
        [Paragraph("Approver", meta_label),
         Paragraph(session.approver_name or "-", meta_value),
         Paragraph("Total findings", meta_label),
         Paragraph(str(len(session.items)), meta_value)],
    ]
    meta_table = Table(
        meta_rows,
        colWidths=[1.05 * inch, 2.35 * inch, 1.05 * inch, 2.40 * inch],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF8")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E6E4DF")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#EDEBE6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)

    story.append(Paragraph("Executive Summary", h_style))
    summary_text = session.executive_summary or _default_summary(session)
    story.append(Paragraph(summary_text.replace("\n", "<br/>"), body_style))

    story.append(Paragraph("Findings", h_style))

    header = [
        Paragraph("#", cell_center),
        Paragraph("Image", cell_center),
        Paragraph("Findings", cell_style),
        Paragraph("Recommendation", cell_style),
        Paragraph("CoF", cell_center),
        Paragraph("Rust grade", cell_center),
    ]
    rows: List[List[Any]] = [header]

    for idx, item in enumerate(session.items, start=1):
        abs_img = storage.load_item_jpeg_path(session.id, item.id)
        if abs_img and abs_img.is_file():
            try:
                img_cell: Any = RLImage(
                    str(abs_img),
                    width=1.0 * inch,
                    height=0.75 * inch,
                    kind="proportional",
                )
            except Exception:
                img_cell = Paragraph("—", cell_center)
        else:
            img_cell = Paragraph("—", cell_center)

        findings_text = (item.findings or item.ai_findings or "—").strip() or "—"
        rec_body = (item.recommendation or item.ai_recommendation or "—").strip() or "—"
        if item.recommendation_code:
            rec_text = f"<b>{item.recommendation_code}</b> — {rec_body}"
        else:
            rec_text = rec_body

        rows.append(
            [
                Paragraph(str(idx), cell_center),
                img_cell,
                Paragraph(findings_text, cell_style),
                Paragraph(rec_text, cell_style),
                Paragraph(str(item.cof) if item.cof is not None else "—", cell_center),
                Paragraph(item.rust_grade or "—", cell_center),
            ]
        )

    if len(rows) == 1:
        rows.append(
            [
                Paragraph("—", cell_center),
                Paragraph("—", cell_center),
                Paragraph("No findings recorded.", cell_style),
                Paragraph("—", cell_style),
                Paragraph("—", cell_center),
                Paragraph("—", cell_center),
            ]
        )

    findings_table = Table(
        rows,
        colWidths=[
            0.30 * inch,
            1.10 * inch,
            2.30 * inch,
            2.30 * inch,
            0.35 * inch,
            0.50 * inch,
        ],
        repeatRows=1,
    )
    findings_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D85A30")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4D1CA")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAF8")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("ALIGN", (4, 1), (5, -1), "CENTER"),
            ]
        )
    )
    story.append(findings_table)

    doc.build(story)
    return path


def list_reports(
    db: Session,
    *,
    q: str = "",
    plant: str = "",
    system_code: str = "",
    preparer: str = "",
    reviewer: str = "",
    approver: str = "",
    status: str = "",
    page: int = 1,
    limit: int = 25,
    sort: str = "submittedAt:desc",
) -> ReportListResponse:
    page = max(1, page)
    limit = max(1, min(100, limit))
    rows = db.query(InspectionSession).all()

    out: List[InspectionSession] = []
    q_norm = q.strip().lower()
    for row in rows:
        if row.status not in REPORT_STATUSES:
            continue
        if status and row.status != status:
            continue
        if plant and plant.lower() not in (row.plant or "").lower():
            continue
        if system_code and system_code.lower() not in (row.system_code or "").lower():
            continue
        if preparer and preparer.lower() not in (row.preparer_name or row.created_by or "").lower():
            continue
        if reviewer and reviewer.lower() not in (row.reviewer_name or "").lower():
            continue
        if approver and approver.lower() not in (row.approver_name or "").lower():
            continue
        if q_norm:
            blob = " ".join(
                [
                    row.system_report_number or _system_report_number(row),
                    row.user_report_number or "",
                    row.plant or "",
                    row.system_code or "",
                    row.preparer_name or row.created_by or "",
                ]
            ).lower()
            if q_norm not in blob:
                continue
        out.append(row)

    sort_key, _, sort_dir = sort.partition(":")
    reverse = (sort_dir or "desc").lower() == "desc"
    key_map = {
        "submittedAt": lambda r: r.submitted_at or r.created_at,
        "createdAt": lambda r: r.created_at,
        "plant": lambda r: (r.plant or "").lower(),
        "systemCode": lambda r: (r.system_code or "").lower(),
    }
    out = sorted(out, key=key_map.get(sort_key, key_map["submittedAt"]), reverse=reverse)
    total = len(out)
    start = (page - 1) * limit
    page_rows = out[start : start + limit]

    return ReportListResponse(
        reports=[_report_summary_row(s) for s in page_rows],
        total=total,
        page=page,
        limit=limit,
    )


def get_report_detail(db: Session, report_id: str) -> ReportDetailOut:
    session = get_session(db, report_id)
    if session.status not in REPORT_STATUSES:
        raise HTTPException(status_code=404, detail="Report not found")
    summary = _report_summary_row(session)
    return ReportDetailOut(
        **summary.model_dump(),
        executiveSummary=session.executive_summary or _default_summary(session),
        createdBy=session.created_by,
        createdAt=session.created_at,
        updatedAt=session.updated_at or session.created_at,
        pdfUrl=_report_pdf_url(session.id) if session.pdf_path else None,
        reviewedAt=session.reviewed_at,
        approvedAt=session.approved_at,
        reviewComment=session.review_comment,
        items=[item_to_out(i) for i in session.items],
    )


def approve_report(db: Session, report_id: str) -> ReportActionOut:
    session = get_session(db, report_id)
    if session.status not in ("submitted", "in_review"):
        raise HTTPException(status_code=400, detail="Report cannot be approved in current status")
    session.status = "approved"
    session.approved_at = _utcnow()
    session.updated_at = _utcnow()
    db.flush()
    return ReportActionOut(id=session.id, status=session.status, message="Report approved")


def request_report_changes(db: Session, report_id: str, comment: str) -> ReportActionOut:
    session = get_session(db, report_id)
    if session.status not in ("submitted", "in_review", "approved"):
        raise HTTPException(status_code=400, detail="Report cannot be sent back in current status")
    session.status = "submitted"
    session.review_comment = comment.strip()
    session.reviewed_at = _utcnow()
    session.approved_at = None
    session.updated_at = _utcnow()
    db.flush()
    return ReportActionOut(
        id=session.id,
        status=session.status,
        message="Changes requested",
    )


def get_report_pdf_path(db: Session, report_id: str) -> str:
    session = get_session(db, report_id)
    if session.status not in REPORT_STATUSES or not session.pdf_path:
        raise HTTPException(status_code=404, detail="Report PDF not found")
    path = _report_pdf_abs_path(session.id)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report PDF not found")
    return path


def delete_report(db: Session, report_id: str) -> DeleteReportOut:
    session = get_session(db, report_id)
    if session.status not in REPORT_STATUSES:
        raise HTTPException(status_code=404, detail="Report not found")
    sid = session.id
    storage.delete_session_dir(sid)
    db.delete(session)
    db.flush()
    return DeleteReportOut(id=sid)


def delete_reports_bulk(db: Session, report_ids: List[str]) -> BulkDeleteReportsResponse:
    deleted: List[str] = []
    failed: List[BulkDeleteFailedItem] = []
    for rid in report_ids:
        if not rid or not str(rid).strip():
            continue
        rid = str(rid).strip()
        try:
            delete_report(db, rid)
            deleted.append(rid)
        except HTTPException as e:
            failed.append(BulkDeleteFailedItem(id=rid, reason=str(e.detail)))
        except Exception as e:
            failed.append(BulkDeleteFailedItem(id=rid, reason=str(e)))
    return BulkDeleteReportsResponse(deleted=deleted, failed=failed)


def submit_session(
    db: Session,
    session_id: str,
    details: Optional[SubmitSessionRequest] = None,
) -> InspectionSessionOut:
    session = get_session(db, session_id)
    if session.status == "submitted":
        return session_to_out(session)
    if not session.items:
        raise HTTPException(status_code=400, detail="No items to submit")

    if details:
        if details.userReportNumber is not None:
            session.user_report_number = details.userReportNumber.strip() or None
        if details.plant is not None:
            session.plant = details.plant.strip() or None
        if details.systemCode is not None:
            session.system_code = details.systemCode.strip() or None
        if details.preparerName is not None:
            session.preparer_name = details.preparerName.strip() or None
        if details.reviewerName is not None:
            session.reviewer_name = details.reviewerName.strip() or None
        if details.approverName is not None:
            session.approver_name = details.approverName.strip() or None

    session.system_report_number = _system_report_number(session)
    if not session.preparer_name:
        session.preparer_name = session.created_by or None
    if not session.executive_summary:
        session.executive_summary = _default_summary(session)

    manifest_items: List[Dict[str, Any]] = []
    for item in session.items:
        bboxes = _parse_bboxes_json(item.ai_bounding_boxes_json)
        storage.write_item_sidecars(
            session_id,
            item.id,
            item.findings or "",
            item.recommendation or "",
            bboxes,
        )
        manifest_items.append(
            {
                "itemId": item.id,
                "code": item.code,
                "imagePath": item.image_path,
                "findingsPath": f"storage/sessions/{session_id}/{item.id}_findings.txt",
                "bboxesPath": f"storage/sessions/{session_id}/{item.id}_bboxes.json",
            }
        )
    pdf_abs_path = _write_report_pdf(session)
    session.pdf_path = f"storage/sessions/{session_id}/executive_report.pdf"
    storage.write_submit_artifacts(
        session_id,
        manifest_items,
        metadata={
            "systemReportNumber": session.system_report_number,
            "userReportNumber": session.user_report_number,
            "pdfPath": session.pdf_path,
        },
    )
    if not os.path.exists(pdf_abs_path):
        raise HTTPException(status_code=500, detail="Failed to generate report PDF")
    session.status = "submitted"
    session.submitted_at = _utcnow()
    session.updated_at = _utcnow()
    db.flush()
    return session_to_out(session)
