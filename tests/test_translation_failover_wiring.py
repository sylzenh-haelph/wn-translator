from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

import pytest

from config.settings import AppConfig, parse_model_chain
from qa.retry_controller import RetryController
from translation import runtime
from translation.model_failover import FailoverModelClient


class FakeClient:
    def __init__(self, name, fail=False):
        self.name = name
        self.fail = fail

    def generate(self, prompt):
        if self.fail:
            raise RuntimeError(f"{self.name} gagal")

        return self.name


class FakeCache:
    def __init__(self):
        self.sets = []

    def build_key(self, **kwargs):
        return "key"

    def get(self, key):
        return None

    def set(self, **kwargs):
        self.sets.append(kwargs)


class FakeEngine:
    def translate(self, **kwargs):
        return SimpleNamespace(
            translation="terjemahan",
            context_state=None,
            paragraph_translations=["terjemahan"],
        )


def fake_qa(source_text, translation, preserved_entities):
    return SimpleNamespace(passed=True, issues=[])


def test_parse_model_chain():
    assert parse_model_chain("") == []
    assert parse_model_chain(
        "gemini:gemma-4-31b-it, gemini:gemini-3.1-flash-lite"
    ) == [
        ("gemini", "gemma-4-31b-it"),
        ("gemini", "gemini-3.1-flash-lite"),
    ]


def test_parse_model_chain_rejects_missing_provider():
    with pytest.raises(ValueError):
        parse_model_chain("gemma-4-31b-it")


def test_parse_model_chain_rejects_openrouter():
    with pytest.raises(ValueError):
        parse_model_chain("openrouter:deepseek/deepseek-r1:free")


def test_translation_client_is_primary_then_fallbacks(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    created = []

    def fake_create(provider, model, api_key, max_retries, timeout, backoff_base):
        created.append((provider, model))
        return FakeClient(f"{provider}:{model}")

    monkeypatch.setattr(runtime, "create_model_client", fake_create)

    config = AppConfig()
    client = runtime.build_translation_client(config)

    assert isinstance(client, FailoverModelClient)
    assert created == [
        ("gemini", "gemma-4-31b-it"),
        ("gemini", "gemini-3.1-flash-lite"),
    ]
    assert client.labels[0] == "gemini:gemma-4-31b-it"


def test_failover_uses_fallback_and_reports_primary():
    events = []
    client = FailoverModelClient(
        [FakeClient("primary", fail=True), FakeClient("backup")],
        labels=["gemini:gemma-4-31b-it", "gemini:gemini-3.1-flash-lite"],
        on_failover=lambda label, exc: events.append(label),
    )

    assert client.generate("x") == "backup"
    assert client.last_used == "gemini:gemini-3.1-flash-lite"
    assert events == ["gemini:gemma-4-31b-it"]


def _run_with_guard(guard_value):
    cache = FakeCache()
    controller = RetryController(
        translation_engine=FakeEngine(),
        qa_function=fake_qa,
        max_retries=0,
        cache=cache,
        cache_model="model",
        cache_guard=lambda: guard_value,
    )
    chunk = SimpleNamespace(
        text="source",
        paragraph_texts=["source"],
    )
    controller.translate_with_retry(
        chunk=chunk,
        chapter_context=None,
        context_state=None,
        entity_resolutions=[],
    )
    return cache.sets


def test_result_not_cached_when_fallback_served():
    assert _run_with_guard(False) == []


def test_result_cached_when_primary_served():
    assert len(_run_with_guard(True)) == 1
