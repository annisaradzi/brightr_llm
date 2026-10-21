"""
RAG service: retrieve top-K historical inspection examples from ChromaDB.
Used by analysis_service.py to inject examples into the Gemini prompt.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Optional

_CHROMA_DIR = Path(os.environ.get("CHROMA_DB_PATH", str(Path(__file__).resolve().parent / "data" / "chroma_db")))
_COLLECTION_NAME = "inspection_history"
_EMBED_MODEL = "all-MiniLM-L6-v2"
_TOP_K = 5

# module-level singletons (lazy-loaded)
_client = None
_collection = None
_model = None


def _load():
    global _client, _collection, _model
    if _collection is not None:
        return True
    try:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        if not _CHROMA_DIR.exists():
            return False

        _client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
        _model = DefaultEmbeddingFunction()
        _collection = _client.get_collection(
            _COLLECTION_NAME,
            embedding_function=_model,
        )
        return True
    except Exception as e:
        print(f"[rag_service] Failed to load RAG index: {e}")
        return False


def _safe_list(val) -> list:
    if not val or val == "[]":
        return []
    try:
        parsed = ast.literal_eval(str(val))
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except Exception:
        return []


def retrieve_examples(
    query_text: str,
    equipment_type: Optional[str] = None,
    component: Optional[str] = None,
    top_k: int = _TOP_K,
) -> list[dict]:
    """
    Return top-K historical inspection examples most similar to query_text.
    Each result is a dict with: finding, recommendations, component,
    equipment_type, extracted_components, extracted_defects, extracted_recommendations.
    """
    if not _load():
        return []

    try:
        query_parts = [query_text]
        if equipment_type:
            query_parts.append(f"Equipment: {equipment_type}")
        if component:
            query_parts.append(f"Component: {component}")

        query = "\n".join(query_parts)
        embedding = _model([query])

        results = _collection.query(
            query_embeddings=embedding,
            n_results=min(top_k, _collection.count()),
            include=["metadatas", "distances"],
        )

        examples = []
        for meta in (results.get("metadatas") or [[]])[0]:
            examples.append({
                "finding":         meta.get("finding", ""),
                "recommendations": meta.get("recommendations", ""),
                "component":       meta.get("component", ""),
                "equipment_type":  meta.get("equipment_type", ""),
                "extracted_components":       _safe_list(meta.get("extracted_components")),
                "extracted_defects":          _safe_list(meta.get("extracted_defects")),
                "extracted_recommendations":  _safe_list(meta.get("extracted_recommendations")),
            })
        return examples

    except Exception as e:
        print(f"[rag_service] Retrieval error: {e}")
        return []


def format_examples_for_prompt(examples: list[dict]) -> str:
    """
    Format retrieved examples into a prompt block Gemini can use as style reference.
    """
    if not examples:
        return ""

    lines = [
        "=========================================================",
        "HISTORICAL INSPECTION EXAMPLES (use ONLY as writing style reference)",
        "DO NOT copy these findings verbatim. Adapt style only.",
        "=========================================================",
    ]
    for i, ex in enumerate(examples, 1):
        lines.append(f"\nExample {i}:")
        if ex.get("equipment_type"):
            lines.append(f"  Equipment type : {ex['equipment_type']}")
        if ex.get("component"):
            lines.append(f"  Component      : {ex['component']}")
        if ex.get("extracted_defects"):
            lines.append(f"  Defects        : {', '.join(ex['extracted_defects'])}")
        if ex.get("finding"):
            lines.append(f"  Finding        : {ex['finding']}")
        if ex.get("recommendations"):
            lines.append(f"  Recommendation : {ex['recommendations']}")
        if ex.get("extracted_recommendations"):
            lines.append(f"  Rec codes      : {', '.join(ex['extracted_recommendations'])}")

    return "\n".join(lines)
