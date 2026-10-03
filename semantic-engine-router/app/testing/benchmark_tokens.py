"""
app/testing/benchmark_tokens.py
================================
Phase 12A — Prompt token-reduction benchmark.

Measures the token savings from exposing 1 unified MCP tool (Universal_Search)
to an LLM instead of 20 individual SerpApi engine tool schemas.

Token counting uses tiktoken with the cl100k_base encoding (GPT-4 / Claude).
No network calls, no SerpApi quota consumed.

Usage
-----
    python -m app.testing.benchmark_tokens
"""

from __future__ import annotations

import json

import tiktoken

from app.testing.mock_tool_schemas import TWENTY_ENGINE_SCHEMAS, UNIVERSAL_SEARCH_SCHEMA

# ---------------------------------------------------------------------------
# Token counter
# ---------------------------------------------------------------------------

_ENCODING = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    """Count GPT-4/cl100k_base tokens in *text*."""
    return len(_ENCODING.encode(text))


# ---------------------------------------------------------------------------
# Core benchmark
# ---------------------------------------------------------------------------


def run_token_benchmark() -> dict:
    """
    Serialize both schema sets to JSON and count tokens.

    Returns
    -------
    dict with keys:
        tokens_20_tools      int   tokens in all 20 engine schemas
        tokens_1_tool        int   tokens in Universal_Search schema
        tokens_saved         int   tokens_20_tools - tokens_1_tool
        percent_reduction    float percentage reduction (0.0 – 100.0)
        tool_count_20        int   always 20
        breakdown            list  per-tool token counts for the 20 schemas
    """
    # Serialize 20 schemas as a JSON array (how an LLM runtime would receive them)
    json_20 = json.dumps(TWENTY_ENGINE_SCHEMAS, indent=2)
    tokens_20 = count_tokens(json_20)

    # Serialize the single Universal_Search schema
    json_1 = json.dumps(UNIVERSAL_SEARCH_SCHEMA, indent=2)
    tokens_1 = count_tokens(json_1)

    tokens_saved = tokens_20 - tokens_1
    percent_reduction = round(tokens_saved / tokens_20 * 100, 1) if tokens_20 else 0.0

    # Per-tool breakdown
    breakdown = []
    for schema in TWENTY_ENGINE_SCHEMAS:
        t = count_tokens(json.dumps(schema, indent=2))
        breakdown.append({"name": schema["name"], "tokens": t})

    return {
        "tokens_20_tools": tokens_20,
        "tokens_1_tool": tokens_1,
        "tokens_saved": tokens_saved,
        "percent_reduction": percent_reduction,
        "tool_count_20": len(TWENTY_ENGINE_SCHEMAS),
        "breakdown": breakdown,
    }


# ---------------------------------------------------------------------------
# CLI report
# ---------------------------------------------------------------------------


def _print_report(r: dict) -> None:
    print()
    print("=" * 68)
    print("  SEMANTIC ENGINE ROUTER -- TOKEN REDUCTION BENCHMARK  (Phase 12A)")
    print("=" * 68)
    print(f"  Encoding        : cl100k_base (GPT-4 / Claude compatible)")
    print(f"  20 tool schemas : {r['tokens_20_tools']:>7,} tokens")
    print(f"  1 tool schema   : {r['tokens_1_tool']:>7,} tokens")
    print(f"  Tokens saved    : {r['tokens_saved']:>7,} tokens")
    print(f"  Reduction       : {r['percent_reduction']:>6.1f}%")
    print("=" * 68)
    print()
    print("  Per-engine token breakdown (sorted by token count):")
    print(f"  {'Tool name':<38} {'Tokens':>7}")
    print(f"  {'-' * 46}")
    for entry in sorted(r["breakdown"], key=lambda x: x["tokens"], reverse=True):
        print(f"  {entry['name']:<38} {entry['tokens']:>7,}")
    print(f"  {'-' * 46}")
    print(f"  {'TOTAL (20 tools)':<38} {r['tokens_20_tools']:>7,}")
    print(f"  {'Universal_Search (1 tool)':<38} {r['tokens_1_tool']:>7,}")
    print()
    print(f"  Result: 1 tool saves {r['tokens_saved']:,} tokens per prompt "
          f"({r['percent_reduction']:.1f}% reduction).")
    print()
    print("=" * 68)
    print()


if __name__ == "__main__":
    _print_report(run_token_benchmark())
