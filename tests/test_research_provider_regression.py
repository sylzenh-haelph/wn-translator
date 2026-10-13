from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from research.research_provider import DuckDuckGoResearchProvider


CHALLENGE_HTML = """
<!DOCTYPE html>
<html>
<head><title>DuckDuckGo</title></head>
<body>
  <p>Unfortunately, bots use DuckDuckGo too.</p>
  <p>Please complete the following challenge to confirm
     this search was made by a human.</p>
  <p>Select all squares containing a duck.</p>
</body>
</html>
"""


class FakeResponse:
    status_code = 202
    text = CHALLENGE_HTML

    def raise_for_status(self):
        pass


class FakeSession:
    def __init__(self):
        self.headers = {}
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return FakeResponse()


def test_challenge_stops_fallback_and_future_requests():
    session = FakeSession()
    provider = DuckDuckGoResearchProvider(
        timeout=1,
        max_retries=0,
        session=session,
    )

    assert provider.search("Mr. Auber") == []
    assert len(session.calls) == 1
    assert session.calls[0][0] == provider.HTML_SEARCH_URL

    # Challenge yang sama tidak seharusnya memicu request baru.
    assert provider.search("another entity") == []
    assert len(session.calls) == 1


def test_empty_query_does_not_send_request():
    session = FakeSession()
    provider = DuckDuckGoResearchProvider(
        timeout=1,
        max_retries=0,
        session=session,
    )

    assert provider.search("   ") == []
    assert session.calls == []


def test_valid_html_results_are_parsed():
    html = """
    <div class="result">
      <h2 class="result__title">
        <a href="https://example.com/mr-auber">Mr. Auber</a>
      </h2>
      <a class="result__snippet">
        A character in the story.
      </a>
    </div>
    """

    session = FakeSession()
    provider = DuckDuckGoResearchProvider(
        timeout=1,
        max_retries=0,
        session=session,
    )
    session.get = lambda url, **kwargs: type(
        "Response",
        (),
        {
            "status_code": 200,
            "text": html,
            "raise_for_status": lambda self: None,
        },
    )()

    results = provider.search("Mr. Auber")

    assert len(results) == 1
    assert results[0].title == "Mr. Auber"
    assert results[0].url == "https://example.com/mr-auber"
    assert results[0].source == "duckduckgo"
    assert provider._challenge_detected is False


def test_empty_results_do_not_trigger_challenge_circuit_breaker():
    session = FakeSession()
    session.get = lambda url, **kwargs: type(
        "Response",
        (),
        {
            "status_code": 200,
            "text": "<html><body>No results</body></html>",
            "raise_for_status": lambda self: None,
        },
    )()

    provider = DuckDuckGoResearchProvider(
        timeout=1,
        max_retries=0,
        session=session,
    )

    assert provider.search("unknown entity") == []
    assert provider._challenge_detected is False
