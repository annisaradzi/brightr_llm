import io
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


REPORTS_DIR = Path("reports")
_MODULE_DIR = Path(__file__).resolve().parent
DEFAULT_LOGO_CANDIDATE = _MODULE_DIR / "assets" / "brightr-logo.png"
MAX_UPLOAD_MB = 10
SUPPORTED_EXTS = ("png", "jpg", "jpeg", "webp")
SYSTEM_PROMPT_PATH = Path("system_prompt")

DEFAULT_SYSTEM_PROMPT = """You are an oil & gas inspection engineer assessing corrosion from an image and its stated severity level.

Your task:
- Identify visible corrosion characteristics and likely implications.
- Provide actionable, practical mitigation/repair recommendations appropriate to the stated severity.
- Optionally list visible defect regions as detections with normalized bounding boxes (0-1 relative to image width/height).

Output requirements (STRICT):
- Return JSON ONLY (no markdown, no code fences, no extra text).
- Use EXACT keys and spelling shown below.
- Use arrays of strings (not a single string) for findings and recommendations.
- Be specific and measurable when possible (location/extent/type, what to do next, how soon).
- If something cannot be determined from the image, say so explicitly as a finding (do not guess).
- For each detection, x,y is top-left; width and height are positive; all values 0-1 (fractions of image size).

Schema:
{
  "summary": "2-3 sentence overview referencing the stated severity level",
  "findings": [
    "3-10 specific observations from the image (what/where/how severe)"
  ],
  "recommendations": [
    "3-10 actionable steps (inspection/NDT, cleaning/prep, repair/replace, coating, monitoring, safety)"
  ],
  "detections": [
    {
      "label": "short label e.g. Pitting",
      "confidence": 0.0,
      "box": { "x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0 }
    }
  ]
}
If there are no localized regions to box, use "detections": [].
"""


def _logo_truetype(size: int, bold: bool = False):
    win = os.environ.get("WINDIR", r"C:\Windows")
    if bold:
        names = ("segoeuib.ttf", "arialbd.ttf", "calibrib.ttf")
    else:
        names = ("segoeui.ttf", "arial.ttf", "calibri.ttf")
    for n in names:
        p = Path(win) / "Fonts" / n
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    for p in (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf")
        if bold
        else Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ):
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _tight_crop_rgba(im: Image.Image) -> Image.Image:
    if im.mode != "RGBA":
        im = im.convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        return im.crop(bbox)
    return im


def _build_brightr_logo_pil() -> Image.Image:
    """Raster brand mark: icon + \"brightr.AI\" (avoids relying on external assets that may be wrong)."""
    W, H = 520, 96
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    orange = (232, 88, 52, 255)
    black = (24, 24, 24, 255)
    cx, cy = 36, 48
    r_outer, r_mid, r_inner = 26, 17, 8
    draw.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), fill=orange)
    draw.ellipse((cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid), fill=(255, 255, 255, 255))
    draw.ellipse((cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner), fill=orange)
    font = _logo_truetype(30, bold=False)
    font_ai = _logo_truetype(30, bold=True)
    y_text = 26
    x = 76
    part1 = "brightr."
    part2 = "AI"
    draw.text((x, y_text), part1, fill=black, font=font)
    bbox = draw.textbbox((x, y_text), part1, font=font)
    x_ai = bbox[2] + 1
    draw.text((x_ai, y_text), part2, fill=orange, font=font_ai)
    return _tight_crop_rgba(img)


def _load_optional_brand_logo_from_disk() -> Optional[Image.Image]:
    """Use BRIGHTR_PDF_LOGO or assets/brightr-logo.png only if dimensions look like a horizontal brand mark."""
    raw = os.getenv("BRIGHTR_PDF_LOGO", "").strip()
    paths: List[Path] = []
    if raw:
        paths.append(Path(raw).expanduser())
    paths.append(DEFAULT_LOGO_CANDIDATE)
    for p in paths:
        if not p.is_file():
            continue
        try:
            im = Image.open(p).convert("RGBA")
        except Exception:
            continue
        w, h = im.size
        if w < 48 or h < 16:
            continue
        aspect = h / float(w)
        if aspect > 0.55:
            continue
        if aspect < 0.1:
            continue
        return _tight_crop_rgba(im)
    return None


def _brand_logo_flowable(max_width: float) -> RLImage:
    pil = _load_optional_brand_logo_from_disk() or _build_brightr_logo_pil()
    pil = _tight_crop_rgba(pil)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    buf.seek(0)
    lw, lh = pil.size
    if lw <= 0 or lh <= 0:
        pil = _build_brightr_logo_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        buf.seek(0)
        lw, lh = pil.size
    w_pt = max_width
    h_pt = w_pt * (float(lh) / float(lw))
    logo = RLImage(buf, width=w_pt, height=h_pt)
    logo.hAlign = "LEFT"
    return logo


@dataclass
class Detection:
    label: str
    box: Dict[str, float]  # x, y, width, height (normalized 0-1)
    confidence: Optional[float] = None


@dataclass
class AnalysisResult:
    summary: str
    findings: List[str]
    recommendations: List[str]
    raw_text: str
    detections: List[Detection] = field(default_factory=list)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _bytes_len_mb(b: bytes) -> float:
    return len(b) / (1024 * 1024)


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None

    cleaned = text.strip()

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    start = cleaned.find("{")
    if start == -1:
        return None

    depth = 0
    for i in range(start, len(cleaned)):
        ch = cleaned[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : i + 1]
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        return obj
                except Exception:
                    return None
    return None


def _normalize_list_str(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, (str, int, float, bool)):
                out.append(str(item).strip())
            else:
                out.append(json.dumps(item, ensure_ascii=False))
        return [x for x in (s.strip() for s in out) if x]
    if isinstance(value, str):
        lines = [ln.strip(" \t-\u2022*") for ln in value.splitlines()]
        return [ln for ln in lines if ln]
    return [str(value).strip()]


def _float01(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f < 0.0 or f > 1.0:
        return None
    return f


def _parse_detections(value: Any) -> List[Detection]:
    if not isinstance(value, list):
        return []
    out: List[Detection] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label", "")).strip()
        if not label:
            continue
        box_raw = item.get("box")
        if not isinstance(box_raw, dict):
            continue
        x = _float01(box_raw.get("x"))
        y = _float01(box_raw.get("y"))
        w = _float01(box_raw.get("width"))
        h = _float01(box_raw.get("height"))
        if x is None or y is None or w is None or h is None:
            continue
        if w <= 0 or h <= 0:
            continue
        conf: Optional[float] = None
        if item.get("confidence") is not None:
            try:
                c = float(item["confidence"])
                if 0.0 <= c <= 1.0:
                    conf = c
            except (TypeError, ValueError):
                pass
        out.append(
            Detection(
                label=label,
                box={"x": x, "y": y, "width": w, "height": h},
                confidence=conf,
            )
        )
    return out


def parse_gemini_response(response_text: str) -> AnalysisResult:
    obj = _extract_first_json_object(response_text)
    if isinstance(obj, dict):
        summary = str(obj.get("summary", "")).strip()
        findings = _normalize_list_str(obj.get("findings"))
        recommendations = _normalize_list_str(obj.get("recommendations"))
        detections = _parse_detections(obj.get("detections"))
        if not summary and (findings or recommendations):
            summary = "See findings and recommendations below."
        return AnalysisResult(
            summary=summary or "No summary provided.",
            findings=findings,
            recommendations=recommendations,
            raw_text=response_text or "",
            detections=detections,
        )

    cleaned = (response_text or "").strip()
    return AnalysisResult(
        summary=cleaned[:600] if cleaned else "No response text returned.",
        findings=[cleaned] if cleaned else [],
        recommendations=[],
        raw_text=response_text or "",
        detections=[],
    )


def _load_system_prompt() -> str:
    prompt = DEFAULT_SYSTEM_PROMPT
    try:
        if SYSTEM_PROMPT_PATH.exists():
            file_text = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
            if file_text:
                prompt = file_text
    except Exception:
        pass
    return prompt


def analyze_image_with_gemini(
    image: Image.Image,
    api_key: str,
    severity: Optional[str] = None,
) -> Tuple[AnalysisResult, str]:
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    model = genai.GenerativeModel(model_name)

    prompt = _load_system_prompt()

    parts: List[Any] = [prompt]
    if severity and str(severity).strip():
        parts.append(f"Stated severity (from user): {str(severity).strip()}")
    parts.append(image)

    try:
        resp = model.generate_content(parts)
        raw_text = getattr(resp, "text", "") or ""
        parsed = parse_gemini_response(raw_text)
        return parsed, raw_text
    except Exception as e:
        raise RuntimeError(f"Gemini analysis failed ({model_name}): {e}") from e


def create_pdf_report(
    *,
    analysis: AnalysisResult,
    report_id: str,
    generated_at: datetime,
    source_filename: Optional[str],
    source_image: Optional[Image.Image] = None,
) -> bytes:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / f"{report_id}.pdf"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title="Image Analysis Report",
        author="Brightr.AI",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=10,
    )
    h_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=14,
        spaceBefore=12,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontSize=10.5,
        leading=14,
        spaceAfter=8,
    )
    cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["BodyText"],
        fontSize=9.5,
        leading=12,
        wordWrap="CJK",
    )

    story: List[Any] = []
    story.append(_brand_logo_flowable(1.65 * inch))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Image Analysis Report", title_style))

    gen_str = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    details_image: Any = Paragraph("No source image provided.", cell_style)
    if source_image is not None:
        image_buffer = io.BytesIO()
        source_image.save(image_buffer, format="JPEG")
        image_buffer.seek(0)
        img_w, img_h = source_image.size
        max_w = 5.9 * inch
        max_h = 3.2 * inch
        scale = min(max_w / float(img_w), max_h / float(img_h), 1.0)
        details_image = RLImage(image_buffer, width=img_w * scale, height=img_h * scale)
        details_image.hAlign = "CENTER"

    metadata_rows = [
        [Paragraph("Generated", cell_style), Paragraph(gen_str, cell_style)],
        [Paragraph("Source", cell_style), Paragraph(source_filename or "-", cell_style)],
        [Paragraph("Report ID", cell_style), Paragraph(report_id, cell_style)],
        [details_image, ""],
    ]
    metadata_table = Table(metadata_rows, colWidths=[1.25 * inch, 5.75 * inch])
    metadata_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("SPAN", (0, 3), (1, 3)),
                ("ALIGN", (0, 3), (1, 3), "CENTER"),
                ("VALIGN", (0, 3), (1, 3), "MIDDLE"),
                ("TOPPADDING", (0, 3), (1, 3), 8),
                ("BOTTOMPADDING", (0, 3), (1, 3), 8),
            ]
        )
    )
    story.append(metadata_table)

    story.append(Spacer(1, 8))
    story.append(Paragraph("Executive Summary", h_style))
    story.append(Paragraph(analysis.summary or "No summary provided.", body_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Key Findings", h_style))
    if analysis.findings:
        rows = [["#", Paragraph("Finding", cell_style)]] + [
            [str(i + 1), Paragraph(f, cell_style)] for i, f in enumerate(analysis.findings)
        ]
        tbl = Table(rows, colWidths=[0.4 * inch, 6.6 * inch])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(tbl)
    else:
        story.append(Paragraph("No findings returned.", body_style))

    if analysis.detections:
        story.append(Spacer(1, 6))
        story.append(Paragraph("Localized detections (VLM, approximate)", h_style))
        d_lines = []
        for d in analysis.detections:
            c = f" (conf. {d.confidence:.0%})" if d.confidence is not None else ""
            b = d.box
            d_lines.append(
                f"- {d.label}{c}: x={b['x']:.3f}, y={b['y']:.3f}, w={b['width']:.3f}, h={b['height']:.3f}"
            )
        story.append(Paragraph("<br/>".join(d_lines), body_style))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Recommendations", h_style))
    if analysis.recommendations:
        rows = [["#", Paragraph("Recommendation", cell_style)]] + [
            [str(i + 1), Paragraph(r, cell_style)] for i, r in enumerate(analysis.recommendations)
        ]
        tbl = Table(rows, colWidths=[0.4 * inch, 6.6 * inch])
        tbl.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9.5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(tbl)
    else:
        story.append(Paragraph("No recommendations returned.", body_style))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    try:
        out_path.write_bytes(pdf_bytes)
    except Exception:
        pass

    return pdf_bytes
