# Semantic Engine Router

> **SerpApi India Hackathon 2026 — Phase 2**

## What Is This?

**Semantic Engine Router** is an MCP-native routing layer that sits between LLM agents and the SerpApi ecosystem. Instead of exposing 15–20 separate SerpApi engine tools to an LLM, this project exposes **one tool** (`Universal_Search`) and uses a lightweight embedding-based semantic classifier to route each natural-language query to the correct SerpApi engine internally (Google Shopping, Scholar, Local, Patents, or base Search).

The classifier uses [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (384-dimensional embeddings) to compute cosine similarity between an incoming query and pre-built per-category centroid vectors. Centroids are cached to disk on first run and reloaded instantly on subsequent server restarts.

---

## Project Structure

```
semantic-engine-router/
├── app/
│   ├── config.py               # pydantic-settings env var loader
│   ├── main.py                 # FastAPI app + /health + POST /classify
│   ├── classifier/
│   │   ├── seed_data.py        # Seed phrases (5 categories × 45+ queries)
│   │   ├── embedder.py         # Lazy-loading SentenceTransformer singleton
│   │   ├── centroids.py        # Build / save / load centroid vectors (.npz)
│   │   └── classify.py         # cosine similarity scoring + classify_top()
│   ├── engines/                # Placeholder — Phase 4+ engine integrations
│   └── mcp/                    # Placeholder — Phase 6 MCP server
├── tests/
│   ├── conftest.py             # Injects dummy SERPAPI_KEY for test runs
│   ├── test_health.py          # /health endpoint smoke test
│   ├── test_seed_data.py       # Validates SEED_PHRASES structure
│   └── test_classifier.py      # Centroid shape, per-engine accuracy, /classify endpoint
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe → `{"status": "ok"}` |
| `POST` | `/classify` | Classify a query → per-engine scores + top-2 ranking |

### POST /classify — Example

**Request**
```json
{ "query": "cheapest noise-cancelling headphones under $200" }
```

**Response**
```json
{
  "query": "cheapest noise-cancelling headphones under $200",
  "scores": {
    "shopping": 0.68,
    "search":   0.21,
    "scholar":  0.18,
    "local":    0.12,
    "patents":  0.09
  },
  "top_2": [["shopping", 0.68], ["search", 0.21]]
}
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/pavaner2007/Nexus_MCP.git
cd Nexus_MCP/semantic-engine-router
```

### 2. Create and activate a virtual environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` pulls in PyTorch (~2 GB). The `all-MiniLM-L6-v2` model weights (~22 MB) are downloaded automatically from HuggingFace on first run.

### 4. Configure environment variables

```bash
# Copy the template and fill in your real SerpApi key
cp .env.example .env
# Edit .env and replace "your_key_here" with your actual key
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive docs: `http://127.0.0.1:8000/docs`

On first startup, centroids are built and cached to `app/classifier/centroids.npz`. Subsequent restarts load from cache instantly.

---

## Running Tests

Tests inject a dummy `SERPAPI_KEY` automatically — **no `.env` file needed**:

```bash
# Standard run
pytest -v

# With stdout (shows ambiguous query results)
pytest -v -s
```

**55 tests across 4 test files** — includes centroid structure, per-engine classification accuracy, ambiguous query separation, JSON float safety, and endpoint shape tests.

### Performance (Phase 2 benchmarks)

| Metric | Result |
|--------|--------|
| `classify()` warm latency | ~13 ms per query |
| Centroid build (cold start) | ~58 s (model download + encode) |
| Centroid load (cached) | < 1 s |

---

## Roadmap

| Phase | Description |
|-------|-------------|
| **1** ✅ | Project scaffold + seed-phrase dataset |
| **2** ✅ | Embedding classifier — centroid scoring + `POST /classify` |
| 3 | Classifier evaluation pipeline + threshold tuning |
| 4 | SerpApi engine integration layer |
| 5 | `Universal_Search` routing logic |
| 6 | MCP server wiring |
| … | Further phases |

---

## License

MIT
