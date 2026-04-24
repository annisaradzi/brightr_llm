import io
import os
import uuid
from typing import Optional

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
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

        try:
            report_id = str(uuid.uuid4())
            generated_at = _now_utc()
            pdf_bytes = create_pdf_report(
                analysis=st.session_state.analysis,
                report_id=report_id,
                generated_at=generated_at,
                source_filename=getattr(uploaded, "name", None) if uploaded is not None else None,
                source_image=image,
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

        if analysis.detections:
            st.subheader("Detections (approximate)")
            for d in analysis.detections:
                c = f" — {d.confidence:.0%}" if d.confidence is not None else ""
                st.caption(f"{d.label}{c}  box={d.box}")

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
