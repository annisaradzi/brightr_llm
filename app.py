import io
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import uuid


REPORTS_DIR = Path("reports")
MAX_UPLOAD_MB = 10
SUPPORTED_EXTS = ("png", "jpg", "jpeg", "webp")
SYSTEM_PROMPT_PATH = Path("system_prompt")


DEFAULT_SYSTEM_PROMPT = """You are an oil & gas inspection engineer assessing corrosion from an image and its stated severity level.

Your task:
- Identify visible corrosion characteristics and likely implications.
- Provide actionable, practical mitigation/repair recommendations appropriate to the stated severity.

Output requirements (STRICT):
- Return JSON ONLY (no markdown, no code fences, no extra text).
- Use EXACT keys and spelling shown below.
- Use arrays of strings (not a single string) for findings and recommendations.
- Be specific and measurable when possible (location/extent/type, what to do next, how soon).
- If something cannot be determined from the image, say so explicitly as a finding (do not guess).

Schema:
{
  "summary": "2-3 sentence overview referencing the stated severity level",
  "findings": [
    "3-10 specific observations from the image (what/where/how severe)"
  ],
  "recommendations": [
    "3-10 actionable steps (inspection/NDT, cleaning/prep, repair/replace, coating, monitoring, safety)"
  ]
}
"""


@dataclass
class AnalysisResult:
    summary: str
    findings: List[str]
    recommendations: List[str]
    raw_text: str


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _bytes_len_mb(b: bytes) -> float:
    return len(b) / (1024 * 1024)


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort extraction of a JSON object from LLM output.
    Handles fenced blocks and "JSON-like" responses.
    """
    if not text:
        return None

    cleaned = text.strip()

    # Remove fenced code blocks if present.
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1).strip()

    # If it's pure JSON already.
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Try to locate the first {...} block.
    start = cleaned.find("{")
    if start == -1:
        return None

    # Scan to find a balanced JSON object.
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
        lines = [ln.strip(" \t-•*") for ln in value.splitlines()]
        return [ln for ln in lines if ln]
    return [str(value).strip()]


def parse_gemini_response(response_text: str) -> AnalysisResult:
    """
    Expected format (preferred):
    {
      "summary": "...",
      "findings": ["..."],
      "recommendations": ["..."]
    }
    Fallback: put raw text into summary and a single finding.
    """
    obj = _extract_first_json_object(response_text)
    if isinstance(obj, dict):
        summary = str(obj.get("summary", "")).strip()
        findings = _normalize_list_str(obj.get("findings"))
        recommendations = _normalize_list_str(obj.get("recommendations"))
        if not summary and (findings or recommendations):
            summary = "See findings and recommendations below."
        return AnalysisResult(
            summary=summary or "No summary provided.",
            findings=findings,
            recommendations=recommendations,
            raw_text=response_text or "",
        )

    # Fallback
    cleaned = (response_text or "").strip()
    return AnalysisResult(
        summary=cleaned[:600] if cleaned else "No response text returned.",
        findings=[cleaned] if cleaned else [],
        recommendations=[],
        raw_text=response_text or "",
    )


def analyze_image_with_gemini(image: Image.Image, api_key: str) -> Tuple[AnalysisResult, str]:
    """
    Returns (parsed_result, raw_text).
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    # Prefer a modern multimodal model; allow fallback if user changes env.
    model_name = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    model = genai.GenerativeModel(model_name)

    prompt = DEFAULT_SYSTEM_PROMPT
    try:
        if SYSTEM_PROMPT_PATH.exists():
            prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip() or DEFAULT_SYSTEM_PROMPT
    except Exception:
        # If prompt file can't be read, fall back to the default prompt.
        prompt = DEFAULT_SYSTEM_PROMPT

    try:
        resp = model.generate_content([prompt, image])
        raw_text = getattr(resp, "text", "") or ""
        parsed = parse_gemini_response(raw_text)
        return parsed, raw_text
    except Exception as e:
        # Let the UI decide how to present this.
        raise RuntimeError(f"Gemini analysis failed ({model_name}): {e}") from e


def create_pdf_report(
    *,
    analysis: AnalysisResult,
    report_id: str,
    generated_at: datetime,
    source_filename: Optional[str],
) -> bytes:
    """
    Create a PDF report and return the PDF bytes.
    Also writes the PDF to `reports/{report_id}.pdf` for convenience.
    """
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
        author="Photo Analysis Pipeline",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=16,
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
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["BodyText"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=10,
    )

    story: List[Any] = []
    story.append(Paragraph("Image Analysis Report", title_style))

    gen_str = generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    meta_bits = [f"Generated: {gen_str}", f"Report ID: {report_id}"]
    if source_filename:
        meta_bits.insert(1, f"Source: {source_filename}")
    story.append(Paragraph(" | ".join(meta_bits), meta_style))

    story.append(Paragraph("Executive Summary", h_style))
    story.append(Paragraph(analysis.summary or "No summary provided.", body_style))

    # Findings table
    story.append(Spacer(1, 6))
    story.append(Paragraph("Key Findings", h_style))
    if analysis.findings:
        rows = [["#", "Finding"]] + [[str(i + 1), f] for i, f in enumerate(analysis.findings)]
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

    # Recommendations table
    story.append(Spacer(1, 10))
    story.append(Paragraph("Recommendations", h_style))
    if analysis.recommendations:
        rows = [["#", "Recommendation"]] + [
            [str(i + 1), r] for i, r in enumerate(analysis.recommendations)
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
        # Writing is best-effort; download still works from memory.
        pass

    return pdf_bytes


def build_ui_shell() -> None:
    st.set_page_config(page_title="Photo Analysis Pipeline", page_icon="📷", layout="centered")
    st.title("Photo Analysis Pipeline")
    st.caption("Upload an image, get findings/recommendations, then download a PDF report.")


def main() -> None:
    load_dotenv()
    build_ui_shell()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        st.warning("Missing `GEMINI_API_KEY`. Create a `.env` from `.env.example` and set your key.")

    if "analysis" not in st.session_state:
        st.session_state.analysis = None
    if "report_bytes" not in st.session_state:
        st.session_state.report_bytes = None
    if "report_filename" not in st.session_state:
        st.session_state.report_filename = None

    uploaded = st.file_uploader(
        "Upload a photo",
        type=list(SUPPORTED_EXTS),
        accept_multiple_files=False,
        help=f"Supported: {', '.join(SUPPORTED_EXTS)}. Max {MAX_UPLOAD_MB}MB.",
    )

    image: Optional[Image.Image] = None
    upload_bytes: Optional[bytes] = None

    if uploaded is not None:
        upload_bytes = uploaded.getvalue()
        if upload_bytes and _bytes_len_mb(upload_bytes) > MAX_UPLOAD_MB:
            st.error(f"File too large: {_bytes_len_mb(upload_bytes):.1f}MB (max {MAX_UPLOAD_MB}MB).")
            return

        try:
            image = Image.open(io.BytesIO(upload_bytes)).convert("RGB")
        except Exception:
            st.error("Could not read that file as an image. Please upload a valid PNG/JPG/WEBP.")
            return

        st.image(image, caption=f"Preview: {uploaded.name}", use_container_width=True)

    analyze_disabled = (image is None) or (not api_key)
    if st.button("Analyze image", type="primary", disabled=analyze_disabled, use_container_width=True):
        st.session_state.analysis = None
        st.session_state.report_bytes = None
        st.session_state.report_filename = None

        raw = ""
        try:
            with st.spinner("Analyzing with Gemini..."):
                parsed, raw = analyze_image_with_gemini(image=image, api_key=api_key)  # type: ignore[arg-type]
                st.session_state.analysis = parsed
        except Exception as e:
            st.session_state.analysis = None
            st.error(str(e))
            if raw:
                with st.expander("Raw model output (debug)"):
                    st.text(raw)
            return

        # Create PDF report immediately after a successful analysis.
        try:
            report_id = str(uuid.uuid4())
            generated_at = _now_utc()
            pdf_bytes = create_pdf_report(
                analysis=st.session_state.analysis,
                report_id=report_id,
                generated_at=generated_at,
                source_filename=getattr(uploaded, "name", None) if uploaded is not None else None,
            )
            st.session_state.report_bytes = pdf_bytes
            st.session_state.report_filename = f"image_analysis_report_{report_id}.pdf"
        except Exception as e:
            st.session_state.report_bytes = None
            st.session_state.report_filename = None
            st.error(f"PDF generation failed: {e}")
            with st.expander("Raw model output (debug)"):
                st.text(raw or "(empty)")

    analysis: Optional[AnalysisResult] = st.session_state.analysis
    if analysis is not None:
        st.subheader("Executive summary")
        st.write(analysis.summary)

        st.subheader("Findings")
        if analysis.findings:
            df_f = pd.DataFrame({"Finding": analysis.findings})
            st.dataframe(df_f, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No findings returned.")

        st.subheader("Recommendations")
        if analysis.recommendations:
            df_r = pd.DataFrame({"Recommendation": analysis.recommendations})
            st.dataframe(df_r, use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No recommendations returned.")

        if st.session_state.report_bytes and st.session_state.report_filename:
            st.subheader("Download report")
            st.download_button(
                "Download PDF report",
                data=st.session_state.report_bytes,
                file_name=st.session_state.report_filename,
                mime="application/pdf",
                use_container_width=True,
            )


if __name__ == "__main__":
    main()
