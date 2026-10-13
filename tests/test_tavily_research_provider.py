from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import requests

from research.research_provider import TavilyResearchProvider


class FakeResponse:
    def __init__(self, data=None, error=None):
        self.data = data or {}
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def test_tavily_parses_results_and_preserves_contract():
    session = FakeSession(FakeResponse({
        "results": [
            {
                "title": "Example character",
                "url": "https://example.com/character",
                "content": "A character from a fantasy novel.",
                "score": 0.92,
            },
            {"title": "", "url": "https://example.com/invalid"},
        ]
    }))
    provider = TavilyResearchProvider(
        api_key="test-key", timeout=3, max_retries=0, session=session
    )

    results = provider.search("Example character", max_results=3)

    assert len(results) == 1
    assert results[0].title == "Example character"
    assert results[0].url == "https://example.com/character"
    assert results[0].snippet == "A character from a fantasy novel."
    assert results[0].source == "tavily"
    assert results[0].relevance == pytest.approx(0.92)
    assert session.calls[0][0] == provider.SEARCH_URL
    assert session.calls[0][1]["json"]["max_results"] == 3
    assert session.calls[0][1]["timeout"] == 3


def test_tavily_empty_query_does_not_send_request():
    session = FakeSession()
    provider = TavilyResearchProvider(
        api_key="test-key", max_retries=0, session=session
    )

    assert provider.search("  ") == []
    assert provider.search("entity", max_results=0) == []
    assert session.calls == []


def test_tavily_missing_api_key_fails_clearly(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with pytest.raises(ValueError, match="TAVILY_API_KEY"):
        TavilyResearchProvider()


def test_tavily_request_failure_returns_empty_results():
    session = FakeSession(FakeResponse(
        error=requests.HTTPError("simulated HTTP error")
    ))
    provider = TavilyResearchProvider(
        api_key="test-key", max_retries=0, session=session
    )

    assert provider.search("entity") == []
    assert len(session.calls) == 1


def test_tavily_retries_transient_request_failure():
    class RetrySession:
        def __init__(self):
            self.calls = 0

        def post(self, url, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise requests.ConnectionError("temporary failure")
            return FakeResponse({
                "results": [{
                    "title": "Recovered",
                    "url": "https://example.com",
                    "content": "Recovered result",
                    "score": 0.8,
                }]
            })

    session = RetrySession()
    provider = TavilyResearchProvider(
        api_key="test-key",
        max_retries=1,
        retry_delay=0,
        session=session,
    )

    assert provider.search("entity")[0].title == "Recovered"
    assert session.calls == 2
