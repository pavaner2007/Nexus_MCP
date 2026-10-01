"""
tests/test_fallback_engine.py
==============================
Unit + live tests for app/engines/fallback.py.

Groups
------
a. Mocked: success with organic results only
b. Mocked: success with answer_box (answer_box placed first)
c. Mocked: success with knowledge_graph (no answer_box)
d. Mocked: SerpApi error response
e. Mocked: empty results (no organic / answer_box / knowledge_graph)
f. Mocked: network exception
g. Live: real SerpApi call (requires SERPAPI_KEY, marked `live`)

Run fast suite (no API calls):
    pytest tests/test_fallback_engine.py -m "not live" -v
"""

from __future__ import annotations

import pytest

from app.engines.fallback import (
    search_fallback,
    _adapt_answer_box,
    _adapt_knowledge_graph,
    _adapt_organic_result,
)
from app.schemas import EngineResponse, EngineResult

# ---------------------------------------------------------------------------
# Mock target
# ---------------------------------------------------------------------------

MOCK_TARGET = "app.engines.fallback.GoogleSearch"

# ---------------------------------------------------------------------------
# Shared fake SerpApi payloads
# ---------------------------------------------------------------------------

FAKE_ORGANIC = [
    {
        "position": 1,
        "title": "Weather in Tirupati",
        "snippet": "Sunny, 32°C. High humidity expected.",
        "link": "https://weather.com/tirupati",
        "displayed_link": "weather.com",
    },
    {
        "position": 2,
        "title": "Tirupati 7-day forecast",
        "snippet": "See the full week ahead.",
        "link": "https://accuweather.com/tirupati",
        "displayed_link": "accuweather.com",
    },
]

FAKE_ANSWER_BOX = {
    "type": "weather_result",
    "title": "Tirupati, Andhra Pradesh",
    "snippet": "32°C, Partly Cloudy",
    "link": "https://weather.com/tirupati",
}

FAKE_KNOWLEDGE_GRAPH = {
    "title": "Tirupati",
    "description": "City in Andhra Pradesh, India known for Tirumala Venkateswara Temple.",
    "website": "https://tirupati.gov.in",
    "image": "https://upload.wikimedia.org/wikipedia/commons/tirupati.jpg",
}

FAKE_SERPAPI_ERROR = {"error": "Invalid API key. Please see https://serpapi.com/manage-api-key"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _mock_search(mocker, payload: dict):
    """Patch GoogleSearch().get_dict() to return ``payload``."""
    mock_instance = mocker.MagicMock()
    mock_instance.get_dict.return_value = payload
    mocker.patch(MOCK_TARGET, return_value=mock_instance)
    return mock_instance


# ---------------------------------------------------------------------------
# (a) Success — organic results only
# ---------------------------------------------------------------------------

class TestSearchFallbackOrganicOnly:
    def _payload(self):
        return {"organic_results": FAKE_ORGANIC}

    def test_returns_engine_response(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather in Tirupati")
        assert isinstance(result, EngineResponse)

    def test_success_true(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather in Tirupati")
        assert result.success is True

    def test_engine_is_search(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather in Tirupati")
        assert result.engine == "search"

    def test_result_count_matches(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather in Tirupati")
        assert result.result_count == len(FAKE_ORGANIC)

    def test_results_are_engine_result_objects(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather in Tirupati")
        assert all(isinstance(r, EngineResult) for r in result.results)

    def test_snippet_contains_source_link(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather in Tirupati")
        # First organic result should have markdown link
        snippet = result.results[0].snippet
        assert "weather.com" in snippet
        assert "http" in snippet

    def test_metadata_source_type_is_organic(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather in Tirupati")
        assert result.results[0].metadata.get("source_type") == "organic"


# ---------------------------------------------------------------------------
# (b) Success — answer_box present (placed first)
# ---------------------------------------------------------------------------

class TestSearchFallbackAnswerBox:
    def _payload(self):
        return {
            "answer_box": FAKE_ANSWER_BOX,
            "organic_results": FAKE_ORGANIC,
        }

    def test_answer_box_is_first_result(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather Tirupati")
        assert result.results[0].metadata.get("source_type") == "answer_box"

    def test_answer_box_title_has_pin_emoji(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather Tirupati")
        assert result.results[0].title.startswith("📌")

    def test_answer_box_snippet_content(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather Tirupati")
        assert "32°C" in result.results[0].snippet

    def test_total_count_includes_answer_box_plus_organic(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("weather Tirupati")
        # 1 answer_box + 2 organic = 3
        assert result.result_count == 1 + len(FAKE_ORGANIC)

    def test_adapt_answer_box_fallback_fields(self):
        """Unit test _adapt_answer_box — answer field used when snippet absent."""
        raw = {"title": "Population", "answer": "5 million", "type": "population"}
        er = _adapt_answer_box(raw)
        assert er.snippet == "5 million"
        assert er.metadata["type"] == "population"


# ---------------------------------------------------------------------------
# (c) Success — knowledge_graph present, no answer_box
# ---------------------------------------------------------------------------

class TestSearchFallbackKnowledgeGraph:
    def _payload(self):
        return {
            "knowledge_graph": FAKE_KNOWLEDGE_GRAPH,
            "organic_results": FAKE_ORGANIC,
        }

    def test_knowledge_graph_is_first_result(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("Tirupati city")
        assert result.results[0].metadata.get("source_type") == "knowledge_graph"

    def test_knowledge_graph_title_has_book_emoji(self, mocker):
        _mock_search(mocker, self._payload())
        result = search_fallback("Tirupati city")
        assert result.results[0].title.startswith("📚")

    def test_knowledge_graph_suppressed_when_answer_box_present(self, mocker):
        """When answer_box is present, knowledge_graph should NOT appear."""
        payload = {
            "answer_box": FAKE_ANSWER_BOX,
            "knowledge_graph": FAKE_KNOWLEDGE_GRAPH,
            "organic_results": FAKE_ORGANIC,
        }
        _mock_search(mocker, payload)
        result = search_fallback("Tirupati weather")
        sources = [r.metadata.get("source_type") for r in result.results]
        assert "knowledge_graph" not in sources
        assert sources[0] == "answer_box"

    def test_adapt_knowledge_graph_website(self):
        """Unit test _adapt_knowledge_graph — website used as link."""
        er = _adapt_knowledge_graph(FAKE_KNOWLEDGE_GRAPH)
        assert er.link == "https://tirupati.gov.in"
        assert "📚" in er.title


# ---------------------------------------------------------------------------
# (d) SerpApi error response
# ---------------------------------------------------------------------------

class TestSearchFallbackSerpApiError:
    def test_returns_failure_response(self, mocker):
        _mock_search(mocker, FAKE_SERPAPI_ERROR)
        result = search_fallback("anything")
        assert result.success is False
        assert result.engine == "search"

    def test_error_message_propagated(self, mocker):
        _mock_search(mocker, FAKE_SERPAPI_ERROR)
        result = search_fallback("anything")
        assert "Invalid API key" in result.error


# ---------------------------------------------------------------------------
# (e) Empty results
# ---------------------------------------------------------------------------

class TestSearchFallbackEmpty:
    def test_empty_returns_success(self, mocker):
        _mock_search(mocker, {"organic_results": []})
        result = search_fallback("xzqjwflaksjdhflkajshdf")
        assert result.success is True

    def test_empty_has_zero_results(self, mocker):
        _mock_search(mocker, {"organic_results": []})
        result = search_fallback("xzqjwflaksjdhflkajshdf")
        assert result.result_count == 0
        assert result.results == []


# ---------------------------------------------------------------------------
# (f) Network exception
# ---------------------------------------------------------------------------

class TestSearchFallbackNetworkError:
    def test_network_error_returns_failure(self, mocker):
        mock_instance = mocker.MagicMock()
        mock_instance.get_dict.side_effect = ConnectionError("timeout")
        mocker.patch(MOCK_TARGET, return_value=mock_instance)
        result = search_fallback("president of India")
        assert result.success is False
        assert "timed out or failed" in result.error


# ---------------------------------------------------------------------------
# (g) Live test — real SerpApi call
# ---------------------------------------------------------------------------

@pytest.mark.live
class TestSearchFallbackLive:
    def test_live_fallback_query(self):
        """Hit real SerpApi with a low-specificity query."""
        result = search_fallback("who is the president of India", num_results=5)
        assert isinstance(result, EngineResponse)
        assert result.success is True
        assert result.result_count > 0
        assert result.engine == "search"
