# Semantic Engine Router

> **SerpApi India Hackathon 2026 — Phase 1**

## What Is This?

**Semantic Engine Router** is an MCP-native routing layer that sits between LLM agents and the SerpApi ecosystem. Instead of exposing 15–20 separate SerpApi engine tools to an LLM, this project exposes **one tool** (`Universal_Search`) and uses a lightweight embedding-based semantic classifier to route each natural-language query to the correct SerpApi engine internally (Google Shopping, Scholar, Local, Patents, or base Search).

This repository contains **Phase 1**: the project scaffold and seed-phrase dataset. Routing logic, the MCP server, and actual SerpApi calls are implemented in later phases.

---

## Project Structure

```
semantic-engine-router/
├── app/
│   ├── config.py          # pydantic-settings env var loader
│   ├── main.py            # FastAPI app + /health endpoint
│   ├── classifier/
│   │   └── seed_data.py   # Seed phrases for training the classifier
│   ├── engines/           # Placeholder — Phase 4+ engine integrations
│   └── mcp/               # Placeholder — Phase 6 MCP server
├── tests/
│   ├── conftest.py        # Injects dummy SERPAPI_KEY for test runs
│   ├── test_health.py     # /health endpoint smoke test
│   └── test_seed_data.py  # Validates SEED_PHRASES structure
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-org/semantic-engine-router.git
cd semantic-engine-router
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

The API will be available at `http://127.0.0.1:8000`. Visit `http://127.0.0.1:8000/health` to confirm the server is running.

---

## Running Tests

Tests inject a dummy `SERPAPI_KEY` automatically, so **no `.env` file is needed** for a test run:

```bash
pytest -v
```

---

## Roadmap

| Phase | Description |
|-------|-------------|
| **1** ✅ | Project scaffold + seed-phrase dataset |
| 2 | Embedding model integration (sentence-transformers) |
| 3 | Classifier training + evaluation pipeline |
| 4 | SerpApi engine integration layer |
| 5 | Universal_Search routing logic |
| 6 | MCP server wiring |
| … | Further phases |

---

## License

MIT
