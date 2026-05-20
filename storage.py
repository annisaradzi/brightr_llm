"""Filesystem storage for session images and export sidecars."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

STORAGE_ROOT = Path(os.getenv("STORAGE_ROOT", "storage")).resolve()


def session_dir(session_id: str) -> Path:
    p = STORAGE_ROOT / "sessions" / session_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_item_jpeg(session_id: str, item_id: str, image: Image.Image) -> str:
    out = session_dir(session_id) / f"{item_id}.jpg"
    image.convert("RGB").save(out, format="JPEG", quality=90)
    return f"storage/sessions/{session_id}/{item_id}.jpg"


def write_submit_artifacts(
    session_id: str,
    manifest_items: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    base = session_dir(session_id)
    manifest_path = base / "manifest.json"
    manifest = {"sessionId": session_id, "items": manifest_items}
    if metadata:
        manifest["report"] = metadata
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def write_item_sidecars(
    session_id: str,
    item_id: str,
    findings_text: str,
    recommendation_text: str,
    bboxes: List[Dict[str, Any]],
) -> None:
    base = session_dir(session_id)
    (base / f"{item_id}_findings.txt").write_text(
        f"FINDINGS\n{findings_text}\n\nRECOMMENDATION\n{recommendation_text}\n",
        encoding="utf-8",
    )
    (base / f"{item_id}_bboxes.json").write_text(json.dumps(bboxes, indent=2), encoding="utf-8")


def load_item_jpeg_path(session_id: str, item_id: str) -> Optional[Path]:
    p = session_dir(session_id) / f"{item_id}.jpg"
    return p if p.is_file() else None
