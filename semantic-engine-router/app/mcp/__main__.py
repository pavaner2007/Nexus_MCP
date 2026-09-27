"""
app/mcp/__main__.py
====================
Runnable entry point for the MCP server.

    python -m app.mcp

CRITICAL: `load_dotenv()` MUST be called BEFORE any `app.*` import.
Claude Desktop and Cursor launch this process in a clean environment where
the shell's exported variables are NOT inherited.  Without `load_dotenv()`
the `SERPAPI_KEY` validation in `app.config` raises a ValidationError and
the server fails to start silently.
"""

# ── dotenv FIRST — before any app imports ──────────────────────────────────
from dotenv import load_dotenv

load_dotenv()  # reads .env from cwd; silently a no-op if the file is absent

# ── now safe to import app modules ─────────────────────────────────────────
from app.mcp.server import mcp  # noqa: E402

if __name__ == "__main__":
    mcp.run()
