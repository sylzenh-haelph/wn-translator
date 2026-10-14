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


def test_research_fallback_default():
    assert AppConfig().research_fallbacks == "gemini:gemini-3.1-flash-lite"
    assert parse_model_chain(AppConfig().research_fallbacks) == [
        ("gemini", "gemini-3.1-flash-lite"),
    ]


def test_research_client_has_fallback_chain(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter")
    created = []

    def fake_create(
        provider,
        model,
        api_key,
        max_retries,
        timeout,
        backoff_base,
    ):
        created.append((provider, model, max_retries, timeout))
        return FakeClient(f"{provider}:{model}")

    monkeypatch.setattr(runtime, "create_model_client", fake_create)

    config = AppConfig(research_fallbacks="gemini:gemini-3.1-flash-lite")

    client = runtime.build_failover_client(
        config,
        role="Research",
        primary_provider="openrouter",
        primary_model="qwen/qwen3.5-35b-a3b",
        fallbacks=config.research_fallbacks,
        max_retries=1,
        timeout=20,
    )

    assert isinstance(client, FailoverModelClient)
    assert created == [
        ("openrouter", "qwen/qwen3.5-35b-a3b", 1, 20),
        ("gemini", "gemini-3.1-flash-lite", 1, 20),
    ]
    assert client.labels == [
        "openrouter:qwen/qwen3.5-35b-a3b",
        "gemini:gemini-3.1-flash-lite",
    ]
