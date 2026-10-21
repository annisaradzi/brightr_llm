# RAG System — Historical Inspection Retrieval

## Why RAG?

Gemini alone doesn't know how *your* engineers write findings and recommendations. Brightr uses Retrieval-Augmented Generation (RAG) to ground every AI analysis in real historical examples from 4,708 past inspections, so Gemini mimics the correct writing style, terminology, and severity grading — without fine-tuning the model.

## Data Source

`data/inspection_dataset_with_extracted.csv` — 4,708 rows with columns:

| Column | Description |
|---|---|
| `equipment_type`, `component` | What was inspected |
| `finding` | Original engineer-written finding text |
| `recommendations` | Original engineer-written recommendation text |
| `extracted_components` | List of components detected via NLP extraction |
| `extracted_defects` | List of defect types detected via NLP extraction |
| `extracted_recommendations` | List of recommendation codes (TBP, TBR, etc.) detected |

## Pipeline

### 1. Build the index (one-time, or after CSV updates)

```bash
python scripts/build_rag_index.py
```

This script ([`scripts/build_rag_index.py`](../scripts/build_rag_index.py)):
1. Loads the CSV with pandas
2. Builds a rich text representation per row (equipment + component + defects + finding + recommendation)
3. Embeds each row using ChromaDB's built-in `DefaultEmbeddingFunction` (ONNX-based, no PyTorch dependency — important since PyTorch has no wheel for Python 3.13 yet)
4. Stores embeddings + metadata in a persistent ChromaDB collection (`inspection_history`)

Output: `data/chroma_db/` (~30MB for 4,708 rows).

### 2. Retrieval at inference time

[`rag_service.py`](../rag_service.py) exposes:

```python
retrieve_examples(query_text, equipment_type=None, component=None, top_k=5)
```

This embeds the query and returns the top-K most similar historical rows (by cosine similarity).

```python
format_examples_for_prompt(examples)
```

Formats retrieved examples into a prompt block:

```
=========================================================
HISTORICAL INSPECTION EXAMPLES (use ONLY as writing style reference)
DO NOT copy these findings verbatim. Adapt style only.
=========================================================

Example 1:
  Equipment type : piping
  Component      : flange
  Defects        : corrosion, coating deterioration
  Finding        : (V1) FLANGE - Localized corrosion...
  Recommendation : TBP. To conduct mechanical cleaning...
  Rec codes      : ['TBP']
```

### 3. Injection into the Gemini prompt

In [`analysis_service.py`](../analysis_service.py), `_load_structured_prompt()` assembles the final prompt in this order:

1. Base instruction ("You are an oil & gas visual inspection engineer...")
2. `recommendation_taxonomy.txt` — allowed recommendation codes
3. `system_prompt` — writing style rules and output format
4. RAG historical examples (from step 2 above)
5. `STRUCTURED_SYSTEM_PROMPT_SUFFIX` — strict JSON schema

## Deployment (Render)

On Render, `start.sh` checks if `CHROMA_DB_PATH` (`/data/chroma_db`) exists on the persistent disk. If not, it runs `build_rag_index.py` automatically on first boot (using the CSV baked into the Docker image), then starts `uvicorn`. Subsequent deploys skip rebuilding unless the disk is wiped.

## Rebuilding the Index

If you update `data/inspection_dataset_with_extracted.csv` with new inspection data:

**Locally:**
```bash
python scripts/build_rag_index.py
```

**On Render:** delete the `chroma_db` folder from the persistent disk (via a one-off shell in the Render dashboard) and redeploy, or SSH in and re-run the script manually.

## Tuning Retrieval Quality

- **Number of examples (`top_k`)** — currently 5. Fewer (3) = more focused but less context; more (8+) = richer context but risk of prompt dilution.
- **Query text** — currently a generic string. For better results, pass the actual equipment type/component from the inspection session context (see `docs/ARCHITECTURE.md` for where this could be wired in `session_service.py`).
- **Embedding model** — currently ChromaDB's default (ONNX MiniLM equivalent). Could be swapped for a domain-specific embedding model if retrieval quality needs improvement.
