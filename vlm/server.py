#!/usr/bin/env python3
"""
Brightr VLM Flask inference service (Moondream2).

Run: python server.py
Default: http://0.0.0.0:5001

POST /analyze — multipart form: image_id (str), image (file)
GET  /health
"""

from __future__ import annotations

import io
import os
import time
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image
from flask.logging import create_logger

from brightr_vlm_moondream import CorrosionInspectionModel

app = Flask(__name__)
CORS(app)
logger = create_logger(app)
logger.info("Starting VLM server")

_MODEL: Optional[CorrosionInspectionModel] = None
_RESULT_CACHE: Dict[str, Dict[str, Any]] = {}

SUPPORTED_EXTS = frozenset({"png", "jpg", "jpeg", "webp"})
MAX_UPLOAD_MB = int(os.getenv("VLM_MAX_UPLOAD_MB", "10"))


def _get_model() -> CorrosionInspectionModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = CorrosionInspectionModel()
    return _MODEL


def _bytes_len_mb(data: bytes) -> float:
    return len(data) / (1024 * 1024)


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "ok": True,
            "model_loaded": _MODEL is not None,
            "cached": len(_RESULT_CACHE),
        }
    )


@app.route("/analyze", methods=["POST"])
def analyze():
    image_id = (request.form.get("image_id") or "").strip()
    if not image_id:
        logger.error("Missing required form field: image_id")
        return jsonify({"error": "Missing required form field: image_id"}), 400

    if image_id in _RESULT_CACHE:
        cached = _RESULT_CACHE[image_id]
        logger.info(f"Returning cached result for image_id: {image_id}")
        return jsonify(
            {
                "imageId": image_id,
                "cached": True,
                "elapsedMs": 0,
                "result": cached["result"],
                "rawOutput": cached.get("rawOutput", ""),
            }
        )

    if "image" not in request.files:
        logger.error("Missing required file field: image")
        return jsonify({"error": "Missing required file field: image"}), 400

    upload = request.files["image"]
    if not upload or not upload.filename:
        logger.error("Empty image upload")
        return jsonify({"error": "Empty image upload"}), 400

    filename = upload.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTS:
        logger.error(f"Unsupported file type '.{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTS))}")
        return jsonify(
            {
                "error": f"Unsupported file type '.{ext}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTS))}"
            }
        ), 400

    data = upload.read()
    if not data:
        logger.error("Empty file upload")
        return jsonify({"error": "Empty file"}), 400
    if _bytes_len_mb(data) > MAX_UPLOAD_MB:
        logger.error(f"File too large (max {MAX_UPLOAD_MB}MB)")
        return jsonify(
            {"error": f"File too large (max {MAX_UPLOAD_MB}MB)"}
        ), 400

    try:
        pil_image = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        logger.error("Could not read image. Use PNG, JPG, or WEBP.")
        return jsonify({"error": "Could not read image. Use PNG, JPG, or WEBP."}), 400

    include_few_shot = os.getenv("VLM_INCLUDE_FEW_SHOT", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    t0 = time.perf_counter()
    try:
        model = _get_model()
        out = model.inference_from_pil(
            pil_image,
            equipment_id=image_id,
            include_few_shot=include_few_shot,
            verbose=False,
        )
    except Exception as e:
        return jsonify({"error": f"Inference failed: {e}"}), 500

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw_output = out.get("raw_output") or ""
    logger.info(f"Inference result: {raw_output}")
    logger.info(f"Inference completed in {elapsed_ms}ms")

    if not out.get("success"):
        payload: Dict[str, Any] = {
            "imageId": image_id,
            "cached": False,
            "elapsedMs": elapsed_ms,
            "error": out.get("error", "Inference failed"),
            "rawOutput": raw_output,
        }
        if out.get("result") is not None:
            payload["result"] = out["result"]
        return jsonify(payload), 422

    result = out["result"]
    _RESULT_CACHE[image_id] = {"result": result, "rawOutput": raw_output}

    return jsonify(
        {
            "imageId": image_id,
            "cached": False,
            "elapsedMs": elapsed_ms,
            "result": result,
            "rawOutput": raw_output,
        }
    )


def main() -> None:
    host = os.getenv("VLM_HOST", "0.0.0.0")
    port = int(os.getenv("VLM_PORT", "5001"))
    preload = os.getenv("VLM_PRELOAD_MODEL", "true").lower() in ("1", "true", "yes")

    if preload:
        print("Preloading Moondream2 model...")
        _get_model()

    app.run(host=host, port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
