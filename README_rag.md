# RAG prototype (ChromaDB + local embeddings + OpenRouter)

Setup and run (Linux/Mac with Python 3.10+):

1. Create and activate your virtualenv, then install:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements_rag.txt
```

2. Copy `.env.example` to `.env` and set your `OPENROUTER_API_KEY` (and optionally `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`).

3. Prepare seed data:

 - Create `seed_data/` in the project root.
 - Add `.txt` files or `.json` files with `{ "text": "...", "metadata": { ... } }`.

4. Ingest seed data into ChromaDB:

```bash
python ingest.py
```

5. Run a quick test generation:

```bash
python test.py
```

Outputs (generated cover letters and provenance) are written to `outputs/cover_letters/`.
