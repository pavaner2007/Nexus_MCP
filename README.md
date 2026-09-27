# Semantic Engine Router

> **SerpApi India Hackathon 2026 — Phase 4**

## What Is This?

**Semantic Engine Router** is an MCP-native routing layer that sits between LLM agents and the SerpApi ecosystem. Instead of exposing 15–20 separate SerpApi engine tools to an LLM, this project exposes **one tool** (`Universal_Search`) and uses a lightweight embedding-based semantic classifier to route each natural-language query to the correct SerpApi engine internally (Google Shopping, Scholar, Local, Patents, or base Search).

The classifier uses [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (384-dimensional embeddings) to compute cosine similarity between an incoming query and pre-built per-category centroid vectors. Centroids are cached to disk on first run and reloaded instantly on subsequent server restarts.

---

## Project Structure

```
semantic-engine-router/
├── app/
│   ├── config.py               # pydantic-settings env var loader
│   ├── main.py                 # FastAPI app + all endpoints
│   ├── classifier/
│   │   ├── seed_data.py        # Seed phrases (5 categories × 45+ queries)
│   │   ├── embedder.py         # Lazy-loading SentenceTransformer singleton
│   │   ├── centroids.py        # Build / save / load centroid vectors (.npz)
│   │   └── classify.py         # Cosine similarity scoring + classify_top()
│   ├── engines/
│   │   ├── shopping.py         # Google Shopping engine (Phase 3)
│   │   └── scholar.py          # Google Scholar engine (Phase 4)
│   └── mcp/                    # Placeholder — Phase 6 MCP server
├── tests/
│   ├── conftest.py             # Injects dummy SERPAPI_KEY for test runs
│   ├── test_health.py          # /health endpoint smoke test
│   ├── test_seed_data.py       # Validates SEED_PHRASES structure
│   ├── test_classifier.py      # Centroid shape, per-engine accuracy, /classify endpoint
│   ├── test_shopping_engine.py # Shopping engine — mocked + live tests
│   └── test_scholar_engine.py  # Scholar engine — mocked + live tests
├── pytest.ini                  # Registers 'live' marker, suppresses warnings
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
| `POST` | `/engines/shopping` | Query Google Shopping → trimmed product results |
| `POST` | `/engines/scholar` | Query Google Scholar → trimmed paper results |

### POST /classify

**Request**
```json
{ "query": "cheapest noise-cancelling headphones under $200" }
```
**Response**
```json
{
  "query": "cheapest noise-cancelling headphones under $200",
  "scores": { "shopping": 0.68, "search": 0.21, "scholar": 0.18, "local": 0.12, "patents": 0.09 },
  "top_2": [["shopping", 0.68], ["search", 0.21]]
}
```

### POST /engines/shopping

**Request**
```json
{ "query": "iPhone 15 Pro", "num_results": 5 }
```
**Response**
```json
{
  "success": true,
  "engine": "shopping",
  "result_count": 5,
  "results": [
    { "title": "Apple iPhone 15 Pro 256GB", "price": "$999.00", "extracted_price": 999.0,
      "source": "Best Buy", "link": "https://...", "thumbnail": "https://...", "rating": 4.8, "reviews": 1234 }
  ]
}
```

### POST /engines/scholar

**Request**
```json
{ "query": "attention is all you need transformer", "num_results": 5 }
```
**Response**
```json
{
  "success": true,
  "engine": "scholar",
  "result_count": 5,
  "results": [
    {
      "title": "Attention Is All You Need",
      "link": "https://arxiv.org/abs/1706.03762",
      "snippet": "The dominant sequence transduction models are based on complex recurrent...",
      "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
      "publication": "Advances in neural information processing systems, 2017",
      "year": "2017",
      "cited_by_count": 98765,
      "pdf_link": "https://arxiv.org/pdf/1706.03762"
    }
  ]
}
```

All engine endpoints share the same error contract:
```json
{ "success": false, "engine": "scholar", "error": "<reason>" }
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
cp .env.example .env
# Edit .env and set your real SerpApi key:
# SERPAPI_KEY=your_actual_key_here
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.  
Interactive docs (Swagger UI): `http://127.0.0.1:8000/docs`

On first startup, centroids are built and cached to `app/classifier/centroids.npz`. Subsequent restarts load from cache instantly.

---

## Running Tests

Tests inject a dummy `SERPAPI_KEY` automatically — **no `.env` file needed** for the fast suite:

```bash
# Fast suite — fully mocked, no network/API key required (101 tests)
pytest -m "not live"

# With stdout — shows ambiguous query classifier results
pytest -m "not live" -s

# Live suite — requires real SERPAPI_KEY in .env, hits actual SerpApi APIs
pytest -m live
```

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
| **3** ✅ | Google Shopping engine + `POST /engines/shopping` |
| **4** ✅ | Google Scholar engine + `POST /engines/scholar` |
| 5 | Local, Patents, Search engines (same pattern) |
| 6 | `Universal_Search` routing — classifier → engine dispatch |
| 7 | MCP server wiring |
| … | Further phases |

---

## License

MIT
