#!/usr/bin/env bash
set -e

CHROMA_DIR="${CHROMA_DB_PATH:-/data/chroma_db}"

echo "==> Checking ChromaDB index at: $CHROMA_DIR"

if [ ! -d "$CHROMA_DIR" ] || [ -z "$(ls -A "$CHROMA_DIR" 2>/dev/null)" ]; then
  echo "==> Index not found. Building ChromaDB index..."
  python scripts/build_rag_index.py
  echo "==> ChromaDB index built."
else
  echo "==> ChromaDB index exists. Skipping build."
fi

echo "==> Starting uvicorn..."
exec uvicorn api_server:app --host 0.0.0.0 --port "${PORT:-8000}"