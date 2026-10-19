# Semantic Engine Router

> **SerpApi India Hackathon 2026 — Phase 14**

## What Is This?

**Semantic Engine Router** is an MCP-native routing layer that sits between LLM agents and the SerpApi ecosystem. Instead of exposing 15–20 separate SerpApi engine tools to an LLM, this project exposes **one tool** (`Universal_Search`) and uses a lightweight embedding-based semantic classifier to route each natural-language query to the correct SerpApi engine internally.

### Routing Modes

| Mode         | Trigger                      | Engines Used                                 |
| ------------ | ---------------------------- | -------------------------------------------- |
| **Single**   | Top score ≥ 0.20, gap > 0.15 | One specialist engine                        |
| **Dual**     | Top score ≥ 0.20, gap ≤ 0.15 | Two engines in parallel via `asyncio.gather` |
| **Fallback** | Top score < 0.20             | Base Google Search                           |

The classifier uses [`all-MiniLM-L6-v2`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) (384-dim embeddings) and cosine similarity against pre-built per-category centroid vectors. Centroids are cached to disk on first run and reloaded instantly on subsequent starts.

Every engine returns a **typed, validated `EngineResponse`** (Pydantic V2) — consistent schema whether calling a REST endpoint or using the MCP tool from Claude Desktop.

---

## Project Structure

```
semantic-engine-router/
├── app/
│   ├── config.py               # pydantic-settings env var loader
│   ├── main.py                 # FastAPI app + all endpoints
│   ├── schemas.py              # Shared EngineResult + EngineResponse Pydantic models
│   ├── classifier/
│   │   ├── seed_data.py        # Seed phrases (5 categories × 45+ queries each)
│   │   ├── embedder.py         # Lazy-loading SentenceTransformer singleton
│   │   ├── centroids.py        # Build / save / load centroid vectors (.npz)
│   │   └── classify.py         # Cosine similarity scoring + classify_top()
│   ├── engines/
│   │   ├── adapters.py         # adapt_*_result() — one per engine
│   │   ├── shopping.py         # Google Shopping engine → EngineResponse
│   │   ├── scholar.py          # Google Scholar engine → EngineResponse
│   │   ├── local.py            # Google Local engine → EngineResponse
│   │   ├── patents.py          # Google Patents engine → EngineResponse
│   │   └── fallback.py         # Base Google Search fallback → EngineResponse
│   ├── routing/
│   │   └── router.py                # decide_route() + async execute_route()
│   ├── demo/
│   │   ├── service.py               # Phase 13: run_demo_query() — full pipeline in one call
│   │   ├── benchmark_store.py       # Phase 14: disk-cached benchmark results (no recompute on load)
│   │   └── cache/                   # JSON cache files (tokens.json, accuracy.json, latency.json)
│   ├── testing/
│   │   ├── eval_dataset.py          # 53-entry hand-labeled FULL_EVAL_SET
│   │   ├── benchmark_accuracy.py    # Phase 11: routing accuracy benchmark CLI
│   │   ├── mock_tool_schemas.py     # Phase 12: 20 engine schemas + Universal_Search
│   │   ├── benchmark_tokens.py      # Phase 12A: token-reduction benchmark CLI
│   │   └── benchmark_latency.py     # Phase 12B: async latency benchmark CLI
│   └── mcp/
│       ├── server.py                # FastMCP server — Universal_Search tool
│       └── __main__.py              # Entry point: python -m app.mcp
├── frontend/                        # Phase 13: Vite + React + TS + Tailwind demo UI
│   ├── src/
│   │   ├── types.ts                 # TypeScript types mirroring backend DemoResult shape
│   │   ├── api.ts                   # Axios client (reads VITE_API_URL)
│   │   ├── App.tsx                  # Main page: header + query bar + panels
│   │   ├── main.tsx                 # TanStack QueryClientProvider entry point
│   │   ├── index.css                # Tailwind + Google Fonts
│   │   └── components/
│   │       ├── QueryBar.tsx         # Search input + example chips
│   │       ├── ScoreBars.tsx        # 5 confidence bars + threshold marker
│   │       ├── RouteBadge.tsx       # SINGLE / DUAL / FALLBACK badge + explanation
│   │       ├── TimingsStrip.tsx     # Classification / engine-call / total ms pills
│   │       ├── ResultCard.tsx       # Engine-specific metadata rendering
│   │       ├── RawJson.tsx          # Collapsible raw JSON inspector
│   │       └── benchmarks/
│   │           ├── TokenSection.tsx     # Phase 14: token comparison chart + schema list
│   │           ├── AccuracySection.tsx  # Phase 14: per-category accuracy chart + misses
│   │           └── LatencySection.tsx   # Phase 14: latency table + empty state
│   ├── pages/
│   │   └── BenchmarksView.tsx       # Phase 14: assembles three benchmark sections
│   ├── .env.example
│   ├── tailwind.config.js
│   └── package.json
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── test_seed_data.py
│   ├── test_classifier.py
│   ├── test_adapters.py
│   ├── test_shopping_engine.py
│   ├── test_scholar_engine.py
│   ├── test_local_engine.py
│   ├── test_patents_engine.py
│   ├── test_fallback_engine.py
│   ├── test_router.py
│   ├── test_mcp_handler.py
│   ├── test_eval_dataset.py
│   ├── test_benchmark_accuracy.py
│   ├── test_benchmark_tokens.py
│   ├── test_benchmark_latency.py
│   ├── test_demo_service.py         # Phase 13: 21 mocked tests for run_demo_query()
│   ├── test_benchmark_store.py      # Phase 14: cache write/read/refresh/unavailable (24 tests)
│   └── test_benchmark_endpoints.py  # Phase 14: 4 benchmark endpoint tests incl. 403 guard (20 tests)
├── pytest.ini                  # Registers 'live' marker, suppresses warnings
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Shared Response Schema

All engines return a validated **`EngineResponse`** Pydantic model. The shape is identical whether you call the REST API or use `Universal_Search` via MCP.

### EngineResponse

```json
{
  "success": true,
  "engine": "shopping",
  "result_count": 2,
  "error": null,
  "classified_as": "shopping",
  "confidence": 0.82,
  "route_detail": null,
  "results": [ ... ]
}
```

> `classified_as`, `confidence`, and `route_detail` are `null` when calling engine endpoints directly.
> In dual-engine mode `route_detail` carries per-engine scores and any partial-failure notes.
> In fallback mode `classified_as` is `"search (fallback)"` and `route_detail` includes a `fallback_reason` string.

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

Common fields (`title`, `snippet`, `link`, `thumbnail`) are always at the top level. Engine-specific extras live in `metadata` so the envelope stays stable as new engines are added.

---

## API Endpoints

| Method | Path                | Description                                          |
| ------ | ------------------- | ---------------------------------------------------- |
| `GET`  | `/health`           | Liveness probe → `{"status": "ok"}`                  |
| `POST` | `/classify`         | Classify a query → per-engine scores + top-2 ranking |
| `POST` | `/engines/shopping` | Query Google Shopping → `EngineResponse`             |
| `POST` | `/engines/scholar`  | Query Google Scholar → `EngineResponse`              |
| `POST` | `/engines/local`    | Query Google Local → `EngineResponse`                |
| `POST` | `/engines/patents`  | Query Google Patents → `EngineResponse`              |

### POST /classify

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
    "search": 0.21,
    "scholar": 0.18,
    "local": 0.12,
    "patents": 0.09
  },
  "top_2": [
    ["shopping", 0.68],
    ["search", 0.21]
  ]
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
    {
      "title": "Apple iPhone 15 Pro 256GB",
      "snippet": "$999.00 from Best Buy",
      "link": "https://...",
      "thumbnail": "https://...",
      "metadata": {
        "price": "$999.00",
        "extracted_price": 999.0,
        "source": "Best Buy",
        "rating": 4.8,
        "reviews": 1234
      }
    }
  ]
}
```

**Error contract (all engines):**

```json
{
  "success": false,
  "engine": "scholar",
  "error": "<reason>",
  "results": [],
  "result_count": 0
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

> Make sure your `.env` file has a real `SERPAPI_KEY` before running.

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

---

## How Routing Works

```
Universal_Search("Tesla showroom near me and current lease pricing")
  |
  +---> classify_top(query, centroids, top_n=2)
  |       => [("local", 0.445), ("shopping", 0.377)]
  |
  +---> decide_route(scores)
  |
  |  top_score=0.445 >= MIN_CONFIDENCE_THRESHOLD (0.20)?  YES
  |  gap = 0.445 - 0.377 = 0.068 <= DUAL_ROUTE_THRESHOLD (0.15)?  YES
  |       => mode="dual"
  |
  +---> execute_route()
          asyncio.gather(search_local(...), search_shopping(...))
          => EngineResponse(
               engine="dual:local+shopping",
               classified_as="dual",
               confidence=0.411,    # average of top-2
               route_detail={"local": 0.445, "shopping": 0.377},
               results=[...local results..., ...shopping results...]
             )
```

### Routing decision table

| top_score | gap     | Mode                               |
| --------- | ------- | ---------------------------------- |
| < 0.20    | any     | **fallback** → base Google Search  |
| >= 0.20   | <= 0.15 | **dual** → two engines in parallel |
| >= 0.20   | > 0.15  | **single** → top-1 engine          |

### Real routing examples

| Query                                    | Mode         | Engine(s)         | Gap   |
| ---------------------------------------- | ------------ | ----------------- | ----- |
| "price of iPhone 15"                     | single       | shopping          | —     |
| "recent papers on transformer attention" | single       | scholar           | —     |
| "coffee shops near me"                   | single       | local             | —     |
| "who holds the CRISPR patent"            | single       | patents           | —     |
| "Tesla showroom + lease pricing"         | **dual**     | local + shopping  | 0.068 |
| "hospitals in Boston ratings + hours"    | **dual**     | local + shopping  | 0.145 |
| "mRNA vaccine prior art at universities" | **dual**     | patents + scholar | 0.057 |
| "what is the temperature in Hyderabad"   | **fallback** | search            | —     |
| "convert 500 USD to INR"                 | **fallback** | search            | —     |

---

## Running Tests

Tests inject a dummy `SERPAPI_KEY` automatically — **no `.env` file needed** for the fast suite:

```bash
# Fast suite — fully mocked, no network/API key required
pytest -m "not live"

# With stdout — shows ambiguous query dual-route diagnostic
pytest -m "not live" -s

# Live suite — requires real SERPAPI_KEY in .env, hits actual SerpApi APIs
pytest -m live
```

### Test Coverage by Module (514 tests total)

| Test File                    | Tests | What It Covers                                                  |
| ---------------------------- | ----- | --------------------------------------------------------------- |
| `test_health.py`             | 1     | `/health` liveness probe                                        |
| `test_seed_data.py`          | 12    | `SEED_PHRASES` structure validation                             |
| `test_classifier.py`         | 16    | Centroid shape, scoring, `/classify` endpoint                   |
| `test_adapters.py`           | 66    | All 4 adapter functions — pure unit tests                       |
| `test_shopping_engine.py`    | 16    | Shopping engine — trim, mock, endpoint, live                    |
| `test_scholar_engine.py`     | 27    | Scholar engine — trim, extract helpers, mock, endpoint, live    |
| `test_local_engine.py`       | 20    | Local engine — trim, mock, endpoint, live                       |
| `test_patents_engine.py`     | 21    | Patents engine — trim, mock, endpoint, live                     |
| `test_fallback_engine.py`    | 20    | Fallback search engine — mock, answer_box, live                 |
| `test_router.py`             | 50    | `decide_route` thresholds, `execute_route` single/dual/fallback |
| `test_mcp_handler.py`        | 24    | `Universal_Search` single/dual/fallback routing + metadata      |
| `test_eval_dataset.py`       | 228   | Structural validation of `FULL_EVAL_SET` (53 entries)           |
| `test_benchmark_accuracy.py` | 13    | Benchmark return-shape + accounting integrity                   |
| `test_benchmark_tokens.py`   | 20    | Token counting, >80% reduction, schema structure                |
| `test_benchmark_latency.py`  | 15    | Mocked latency benchmark — shape, ordering, meta                |

### Performance

| Metric                                                     | Result                          |
| ---------------------------------------------------------- | ------------------------------- |
| `classify()` warm latency                                  | ~13 ms per query                |
| Centroid build (cold start)                                | ~58 s (model download + encode) |
| Centroid load (cached)                                     | < 1 s                           |
| Benchmark CLI (`python -m app.testing.benchmark_accuracy`) | ~39 s (53 queries, model warm)  |
| Token benchmark (`python -m app.testing.benchmark_tokens`) | < 1 s                           |
| Token reduction (1 tool vs 20 tools)                       | **97.4%** (7,116 → 187 tokens)  |

---

## Evaluation Dataset

Located at `app/testing/eval_dataset.py`, the `FULL_EVAL_SET` is a **53-entry hand-labeled benchmark** used by Phase 11+ accuracy tests.

| Subset        | Count  | Description                                                                             |
| ------------- | ------ | --------------------------------------------------------------------------------------- |
| Single-engine | 40     | 8 per category (shopping, scholar, local, patents, search) — 6 clear + 2 borderline     |
| Dual-engine   | 8      | Wrapped from `AMBIGUOUS_TEST_QUERIES`; each has `expected_dual_categories=[cat1, cat2]` |
| Fallback      | 5      | Generic/low-confidence queries that should score below `MIN_CONFIDENCE_THRESHOLD`       |
| **Total**     | **53** |                                                                                         |

**Held-out guarantee:** all 53 queries are verified to have zero overlap with `SEED_PHRASES` via normalised string comparison (lowercase + strip trailing punctuation). Enforced by `test_eval_dataset.py`.

```python
from app.testing.eval_dataset import FULL_EVAL_SET, TestCase

# TestCase fields:
#   query                    str
#   expected_mode            "single" | "dual" | "fallback"
#   expected_category        str | None        # set for single/fallback
#   expected_dual_categories list[str] | None  # [cat1, cat2] for dual
#   notes                    str               # nuance explanation for borderline cases
```

---

## Running Accuracy Benchmark

```bash
python -m app.testing.benchmark_accuracy
```

Runs all 53 `FULL_EVAL_SET` queries through the real classifier + router pipeline (no SerpApi calls). Outputs a per-category accuracy table and full miss list with confidence scores.

**Phase 11 baseline results (`MIN_CONFIDENCE_THRESHOLD = 0.20`):**

| Category    | Total  | Correct | Accuracy  |
| ----------- | ------ | ------- | --------- |
| shopping    | 8      | 7       | 87.5%     |
| scholar     | 8      | 4       | 50.0%     |
| local       | 8      | 5       | 62.5%     |
| patents     | 8      | 7       | 87.5%     |
| search      | 8      | 0       | 0.0%      |
| dual        | 8      | 4       | 50.0%     |
| fallback    | 5      | 4       | 80.0%     |
| **Overall** | **53** | **31**  | **58.5%** |

**Key failure modes identified:**

- **`search` (0%):** The `search` centroid scores low across the board; queries either fall below the confidence threshold (routed to fallback) or get dual-routed with scholar due to a small gap.
- **`scholar` (50%):** Very specific academic queries (preprints, systematic reviews) score below 0.20 and fall to fallback.
- **4 of 8 `dual` misses are correct routing:** The classifier correctly identified a dominant single engine where the eval label expected dual (patents gap too wide to trigger dual).

> `MIN_CONFIDENCE_THRESHOLD` was calibrated from `0.35` to `0.20` after Phase 11 revealed 0.35 was incorrectly routing valid single-engine queries to fallback.

---

## Roadmap

| Phase     | Description                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------ |
| **1** ✅  | Project scaffold + seed-phrase dataset (5 categories × 45+ queries)                              |
| **2** ✅  | Embedding classifier — centroid scoring + `POST /classify`                                       |
| **3** ✅  | Google Shopping engine + `POST /engines/shopping`                                                |
| **4** ✅  | Google Scholar engine + `POST /engines/scholar`                                                  |
| **5** ✅  | MCP server — `Universal_Search` tool, classifier → engine routing                                |
| **6** ✅  | Pydantic schema (`EngineResponse`/`EngineResult`) + adapter layer                                |
| **7** ✅  | Local + Patents engines + `POST /engines/local` + `POST /engines/patents`                        |
| **8** ✅  | Dual-engine routing — `decide_route()` + `async execute_route()`                                 |
| **9** ✅  | Fallback routing — `search_fallback()`, `MIN_CONFIDENCE_THRESHOLD` — 269 tests                   |
| **10** ✅ | Hand-labeled eval dataset — 53 queries across 3 routing modes — 497 tests                        |
| **11** ✅ | Routing-accuracy benchmark — 58.5% baseline, threshold calibrated 0.35→0.20 — 514 tests          |
| **12** ✅ | Token + latency benchmarks — 97.4% token reduction, async latency across all 3 modes — 544 tests |
| **13** ✅ | Live demo UI — React + Vite + Tailwind, `/demo/search` + `/demo/examples`, confidence bars with threshold marker — 565 tests |
| **14** ✅ | Benchmarks tab — cached token/accuracy/latency endpoints, recharts UI, 403 guard — 593 tests |

---

## License

MIT
