# Semantic Engine Router

> **SerpApi India Hackathon 2026 — Phase 6**

## What Is This?

**Semantic Engine Router** is an MCP-native routing layer that sits between LLM agents and the SerpApi ecosystem. Instead of exposing 15–20 separate SerpApi engine tools to an LLM, this project exposes **one tool** (`Universal_Search`) and uses a lightweight embedding-based semantic classifier to route each natural-language query to the correct SerpApi engine internally (Google Shopping, Scholar, Local, Patents, or base Search).

The classifier uses [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (384-dimensional embeddings) to compute cosine similarity between an incoming query and pre-built per-category centroid vectors. Centroids are cached to disk on first run and reloaded instantly on subsequent server restarts.

Every engine returns a **typed, validated `EngineResponse`** (Pydantic V2) so the schema is consistent whether you're calling a REST endpoint or using the MCP tool from Claude Desktop.

---

## Project Structure

```
semantic-engine-router/
├── app/
│   ├── config.py               # pydantic-settings env var loader
│   ├── main.py                 # FastAPI app + all endpoints
│   ├── schemas.py              # Shared EngineResult + EngineResponse Pydantic models (Phase 6)
│   ├── classifier/
│   │   ├── seed_data.py        # Seed phrases (5 categories × 45+ queries)
│   │   ├── embedder.py         # Lazy-loading SentenceTransformer singleton
│   │   ├── centroids.py        # Build / save / load centroid vectors (.npz)
│   │   └── classify.py         # Cosine similarity scoring + classify_top()
│   ├── engines/
│   │   ├── adapters.py         # adapt_shopping_result() + adapt_scholar_result() (Phase 6)
│   │   ├── shopping.py         # Google Shopping engine → EngineResponse
│   │   └── scholar.py          # Google Scholar engine → EngineResponse
│   └── mcp/
│       ├── server.py           # FastMCP server — Universal_Search tool
│       └── __main__.py         # Entry point: python -m app.mcp
├── tests/
│   ├── conftest.py             # Injects dummy SERPAPI_KEY for test runs
│   ├── test_health.py          # /health endpoint smoke test
│   ├── test_seed_data.py       # Validates SEED_PHRASES structure
│   ├── test_classifier.py      # Centroid shape, per-engine accuracy, /classify endpoint
│   ├── test_adapters.py        # Pure unit tests for adapter functions (Phase 6)
│   ├── test_shopping_engine.py # Shopping engine — mocked + live tests
│   ├── test_scholar_engine.py  # Scholar engine — mocked + live tests
│   └── test_mcp_handler.py     # Universal_Search routing, stubs, metadata injection
├── pytest.ini                  # Registers 'live' marker, suppresses warnings
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Shared Response Schema (Phase 6)

All engines now return a validated **`EngineResponse`** Pydantic model. The shape is identical whether you call the REST API or use `Universal_Search` via MCP.

### EngineResponse

```json
{
  "success": true,
  "engine": "shopping",
  "result_count": 2,
  "error": null,
  "classified_as": "shopping",
  "confidence": 0.82,
  "results": [ ... ]
}
```

> `classified_as` and `confidence` are `null` when calling engine endpoints directly. They are populated by the MCP router after classification.

### EngineResult

```json
{
  "title": "Apple iPhone 15 128GB",
  "snippet": "$799.00 from Best Buy",
  "link": "https://bestbuy.com/iphone15",
  "thumbnail": "https://cdn.example.com/iphone15.jpg",
  "metadata": {
    "price": "$799.00",
    "extracted_price": 799.0,
    "source": "Best Buy",
    "rating": 4.8,
    "reviews": 1234
  }
}
```

Common fields (`title`, `snippet`, `link`, `thumbnail`) are always at the top level. Engine-specific extras (`price`, `authors`, `cited_by_count`, etc.) live in `metadata` so the envelope stays stable as new engines are added.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness probe → `{"status": "ok"}` |
| `POST` | `/classify` | Classify a query → per-engine scores + top-2 ranking |
| `POST` | `/engines/shopping` | Query Google Shopping → `EngineResponse` |
| `POST` | `/engines/scholar` | Query Google Scholar → `EngineResponse` |

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
  "error": null,
  "classified_as": null,
  "confidence": null,
  "results": [
    {
      "title": "Apple iPhone 15 Pro 256GB",
      "snippet": "$999.00 from Best Buy",
      "link": "https://...",
      "thumbnail": "https://...",
      "metadata": { "price": "$999.00", "extracted_price": 999.0, "source": "Best Buy", "rating": 4.8, "reviews": 1234 }
    }
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
  "error": null,
  "classified_as": null,
  "confidence": null,
  "results": [
    {
      "title": "Attention Is All You Need",
      "snippet": "The dominant sequence transduction models are based on complex recurrent...",
      "link": "https://arxiv.org/abs/1706.03762",
      "thumbnail": null,
      "metadata": {
        "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
        "publication": "Advances in neural information processing systems, 2017",
        "year": "2017",
        "cited_by_count": 98765,
        "pdf_link": "https://arxiv.org/pdf/1706.03762"
      }
    }
  ]
}
```

**Error contract (all engines):**
```json
{ "success": false, "engine": "scholar", "error": "<reason>", "results": [], "result_count": 0 }
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

## Running the MCP Server

Start the MCP server directly (used by Claude Desktop / Cursor):

```bash
python -m app.mcp
```

> Make sure your `.env` file has a real `SERPAPI_KEY` before running. The server loads it automatically via `python-dotenv`.

---

## Connecting to Claude Desktop

Add the following to your `claude_desktop_config.json`  
(usually at `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "semantic-engine-router": {
      "command": "C:\\path\\to\\semantic-engine-router\\.venv\\Scripts\\python.exe",
      "args": ["-m", "app.mcp"],
      "cwd": "C:\\path\\to\\semantic-engine-router",
      "env": {
        "SERPAPI_KEY": "your_actual_serpapi_key_here"
      }
    }
  }
}
```

> **Replace** `C:\\path\\to\\semantic-engine-router` with the actual absolute path to your `semantic-engine-router` directory.  
> **Replace** `your_actual_serpapi_key_here` with your real SerpApi key.

After saving, restart Claude Desktop. The **Universal_Search** tool will appear in Claude's tool list.

**Try asking Claude:**
- *"What's the price of iPhone 15 Pro?"* → routes to Shopping → returns `EngineResponse` with price/source in metadata
- *"Recent papers on transformer attention mechanisms"* → routes to Scholar → returns `EngineResponse` with authors/citations in metadata
- *"Coffee shops near me"* → returns stub (Local engine — Phase 7)

---

## Running Tests

Tests inject a dummy `SERPAPI_KEY` automatically — **no `.env` file needed** for the fast suite:

```bash
# Fast suite — fully mocked, no network/API key required (147 tests)
pytest -m "not live"

# With stdout — shows ambiguous query classifier results
pytest -m "not live" -s

# Live suite — requires real SERPAPI_KEY in .env, hits actual SerpApi APIs
pytest -m live
```

### Test Coverage by Module

| Test File | Tests | What It Covers |
|---|---|---|
| `test_health.py` | 1 | `/health` liveness probe |
| `test_seed_data.py` | 12 | SEED_PHRASES structure validation |
| `test_classifier.py` | 16 | Centroid shape, scoring, `/classify` endpoint |
| `test_adapters.py` | 34 | `adapt_shopping_result()` + `adapt_scholar_result()` pure unit tests |
| `test_shopping_engine.py` | 38 | Shopping engine — trim, mock, endpoint, live |
| `test_scholar_engine.py` | 30 | Scholar engine — trim, extract helpers, mock, endpoint, live |
| `test_mcp_handler.py` | 16 | `Universal_Search` routing, stubs, metadata injection |

### Performance Benchmarks

| Metric | Result |
|--------|--------|
| `universal_search()` end-to-end (cached centroids) | ~15 ms classify + engine latency |
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
| **5** ✅ | MCP server — `Universal_Search` tool, classifier → engine routing |
| **6** ✅ | Pydantic schema (`EngineResponse`/`EngineResult`) + adapter layer — 147 tests |
| 7 | Local, Patents, Search engines |
| 8 | Fallback + dual-engine merging |
| … | Further phases |

---

## License

MIT
