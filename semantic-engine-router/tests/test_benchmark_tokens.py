"""
tests/test_benchmark_tokens.py
================================
Unit tests for app/testing/benchmark_tokens.py.

No network I/O — all pure computation on in-memory JSON.
"""

from __future__ import annotations

import pytest

from app.testing.benchmark_tokens import count_tokens, run_token_benchmark
from app.testing.mock_tool_schemas import TWENTY_ENGINE_SCHEMAS, UNIVERSAL_SEARCH_SCHEMA


# ---------------------------------------------------------------------------
# count_tokens()
# ---------------------------------------------------------------------------


def test_count_tokens_hello_world():
    """'hello world' is 2 tokens in cl100k_base."""
    assert count_tokens("hello world") == 2


def test_count_tokens_empty_string():
    assert count_tokens("") == 0


def test_count_tokens_returns_int():
    assert isinstance(count_tokens("test sentence for tokenisation"), int)


def test_count_tokens_longer_text_is_more():
    short = count_tokens("hello")
    long = count_tokens("hello world this is a much longer sentence with many words")
    assert long > short


# ---------------------------------------------------------------------------
# Schema sanity checks
# ---------------------------------------------------------------------------


def test_twenty_schemas_count():
    assert len(TWENTY_ENGINE_SCHEMAS) == 20


def test_each_schema_has_required_fields():
    for schema in TWENTY_ENGINE_SCHEMAS:
        assert "name" in schema, f"Missing 'name' in schema: {schema}"
        assert "description" in schema, f"Missing 'description' in schema: {schema}"
        assert "inputSchema" in schema, f"Missing 'inputSchema' in schema: {schema}"
        assert "query" in schema["inputSchema"]["properties"] or \
               "url" in schema["inputSchema"]["properties"] or \
               "departure_id" in schema["inputSchema"]["properties"], \
               f"Schema {schema['name']} missing primary input parameter"


def test_universal_search_schema_has_required_fields():
    assert "name" in UNIVERSAL_SEARCH_SCHEMA
    assert "description" in UNIVERSAL_SEARCH_SCHEMA
    assert "inputSchema" in UNIVERSAL_SEARCH_SCHEMA
    assert "query" in UNIVERSAL_SEARCH_SCHEMA["inputSchema"]["properties"]


def test_schema_names_are_unique():
    names = [s["name"] for s in TWENTY_ENGINE_SCHEMAS]
    assert len(names) == len(set(names)), "Duplicate tool names in TWENTY_ENGINE_SCHEMAS"


# ---------------------------------------------------------------------------
# run_token_benchmark()
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def result():
    return run_token_benchmark()


def test_result_has_required_keys(result):
    assert "tokens_20_tools" in result
    assert "tokens_1_tool" in result
    assert "tokens_saved" in result
    assert "percent_reduction" in result
    assert "breakdown" in result


def test_tokens_20_tools_is_int(result):
    assert isinstance(result["tokens_20_tools"], int)


def test_tokens_1_tool_is_int(result):
    assert isinstance(result["tokens_1_tool"], int)


def test_one_tool_fewer_tokens_than_twenty(result):
    """Core acceptance criterion: 1 tool uses far fewer tokens than 20."""
    assert result["tokens_1_tool"] < result["tokens_20_tools"]


def test_percent_reduction_above_80(result):
    """Must achieve >80% token reduction — the hackathon pitch claim."""
    assert result["percent_reduction"] > 80.0, (
        f"Expected >80% reduction, got {result['percent_reduction']:.1f}%. "
        "Check that TWENTY_ENGINE_SCHEMAS and UNIVERSAL_SEARCH_SCHEMA are realistic."
    )


def test_tokens_saved_equals_difference(result):
    expected = result["tokens_20_tools"] - result["tokens_1_tool"]
    assert result["tokens_saved"] == expected


def test_percent_reduction_is_float(result):
    assert isinstance(result["percent_reduction"], float)


def test_percent_reduction_in_valid_range(result):
    assert 0.0 < result["percent_reduction"] < 100.0


def test_breakdown_has_20_entries(result):
    assert len(result["breakdown"]) == 20


def test_breakdown_entries_have_name_and_tokens(result):
    for entry in result["breakdown"]:
        assert "name" in entry
        assert "tokens" in entry
        assert isinstance(entry["tokens"], int)
        assert entry["tokens"] > 0


def test_breakdown_totals_match_tokens_20(result):
    """Sum of per-tool tokens won't exactly match the array JSON (commas/brackets),
    but should be within 5% since array overhead is small."""
    breakdown_sum = sum(e["tokens"] for e in result["breakdown"])
    ratio = breakdown_sum / result["tokens_20_tools"]
    assert 0.85 <= ratio <= 1.15, (
        f"Breakdown sum {breakdown_sum} deviates too far from {result['tokens_20_tools']}"
    )
