from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from config.settings import AppConfig, parse_model_chain
from translation import runtime
from translation.model_failover import FailoverModelClient


class FakeClient:
    def __init__(self, name):
        self.name = name


def test_research_defaults_use_gemini_with_gemma_fallback():
    config = AppConfig()

    assert config.research_provider == "gemini"
    assert config.research_model == "gemini-3.1-flash-lite"
    assert parse_model_chain(config.research_fallbacks) == [
        ("gemini", "gemma-4-31b-it"),
        ("gemini", "gemini-3-flash-preview"),
    ]


def test_research_client_has_fallback_chain(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    created = []

    def fake_create(provider, model, api_key, max_retries, timeout, backoff_base):
        created.append((provider, model, max_retries, timeout))
        return FakeClient(f"{provider}:{model}")

    monkeypatch.setattr(runtime, "create_model_client", fake_create)

    config = AppConfig()

    client = runtime.build_failover_client(
        config,
        role="Research",
        primary_provider=config.research_provider,
        primary_model=config.research_model,
        fallbacks=config.research_fallbacks,
        max_retries=1,
        timeout=20,
    )

    assert isinstance(client, FailoverModelClient)
    assert created == [
        ("gemini", "gemini-3.1-flash-lite", 1, 20),
        ("gemini", "gemma-4-31b-it", 1, 20),
        ("gemini", "gemini-3-flash-preview", 1, 20),
    ]
    assert client.labels == [
        "gemini:gemini-3.1-flash-lite",
        "gemini:gemma-4-31b-it",
        "gemini:gemini-3-flash-preview",
    ]
