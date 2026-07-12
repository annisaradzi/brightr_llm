"""
One-time script to embed 4000 inspection rows into ChromaDB.
Run from repo root:
    python scripts/build_rag_index.py
"""

import ast
import os
import sys
from pathlib import Path

import pandas as pd

# --- config (override via env vars on Render) ---
CSV_PATH = Path(os.environ.get("RAG_CSV_PATH", "data/inspection_dataset_with_extracted.csv"))
CHROMA_DIR = Path(os.environ.get("CHROMA_DB_PATH", "data/chroma_db"))
COLLECTION_NAME = "inspection_history"
BATCH_SIZE = 100

def safe_list(val) -> list:
    """Parse stringified list or return empty list."""
    if not val or (isinstance(val, float)):
        return []
    if isinstance(val, list):
        return val
    try:
        parsed = ast.literal_eval(str(val))
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except Exception:
        return [str(val)]


def build_embed_text(row) -> str:
    """Build a rich text string for embedding from a row."""
    parts = []

    if row.get("equipment_type"):
        parts.append(f"Equipment: {row['equipment_type']}")
    if row.get("component"):
        parts.append(f"Component: {row['component']}")

    components = safe_list(row.get("extracted_components"))
    if components:
        parts.append(f"Components: {', '.join(components)}")

    defects = safe_list(row.get("extracted_defects"))
    if defects:
        parts.append(f"Defects: {', '.join(defects)}")

    if row.get("finding"):
        parts.append(f"Finding: {row['finding']}")

    recs = safe_list(row.get("extracted_recommendations"))
    if recs:
        parts.append(f"Recommendation codes: {', '.join(recs)}")

    if row.get("recommendations"):
        parts.append(f"Recommendations: {row['recommendations']}")

    return "\n".join(parts)


def main():
    try:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    except ImportError:
        print("Missing dependencies. Run:")
        print("  pip install chromadb")
        sys.exit(1)

    print(f"Loading CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

    # drop rows with no finding
    df = df[df["finding"].notna() & (df["finding"].str.strip() != "")]
    print(f"Rows with valid finding: {len(df)}")

    print("Using ChromaDB default embedding function (no torch required).")
    embed_fn = DefaultEmbeddingFunction()

    print(f"Setting up ChromaDB at: {CHROMA_DIR}")
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # delete existing collection if rebuilding
    try:
        client.delete_collection(COLLECTION_NAME)
        print("Deleted existing collection.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    rows = df.to_dict(orient="records")
    total = len(rows)

    for i in range(0, total, BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        texts, ids, metadatas = [], [], []

        for row in batch:
            iid = str(row.get("inspection_id", f"row_{i}"))
            text = build_embed_text(row)
            texts.append(text)
            ids.append(iid)
            metadatas.append({
                "inspection_id":   str(row.get("inspection_id", "")),
                "equipment_type":  str(row.get("equipment_type", "") or ""),
                "component":       str(row.get("component", "") or ""),
                "finding":         str(row.get("finding", "") or "")[:1000],
                "recommendations": str(row.get("recommendations", "") or "")[:500],
                "extracted_components":      str(safe_list(row.get("extracted_components"))),
                "extracted_defects":         str(safe_list(row.get("extracted_defects"))),
                "extracted_recommendations": str(safe_list(row.get("extracted_recommendations"))),
            })

        collection.add(documents=texts, ids=ids, metadatas=metadatas)
        print(f"  Indexed {min(i + BATCH_SIZE, total)}/{total} rows...")

    print(f"\nDone. ChromaDB index saved at: {CHROMA_DIR}")
    print(f"Collection '{COLLECTION_NAME}' has {collection.count()} entries.")


if __name__ == "__main__":
    main()
