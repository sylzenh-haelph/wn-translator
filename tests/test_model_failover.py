from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

import pytest

from translation import model_client as mc
from translation.model_client import ModelProviderError, OpenRouterClient
from translation.model_failover import FailoverModelClient


class Failing:
    def __init__(self, exc):
        self.exc = exc

    def generate(self, prompt):
        raise self.exc


class Working:
    def __init__(self, text):
        self.text = text

    def generate(self, prompt):
        return self.text


def test_primary_used_when_healthy():
    client = FailoverModelClient(
        [Working("primary"), Working("backup")],
        labels=["main", "backup"],
    )

    assert client.generate("x") == "primary"
    assert client.last_used == "main"


def test_fails_over_on_provider_error_and_records_label():
    primary = Failing(
        ModelProviderError(
            "OpenRouter API HTTP 402",
            provider="openrouter",
            status_code=402,
        )
    )
    client = FailoverModelClient(
        [primary, Working("backup")],
        labels=["hy-mt2", "gemma"],
    )

    assert client.generate("x") == "backup"
    assert client.last_used == "gemma"


def test_failover_callback_is_called():
    seen = []
    client = FailoverModelClient(
        [Failing(RuntimeError("boom")), Working("ok")],
        labels=["a", "b"],
        on_failover=lambda label, exc: seen.append(label),
    )

    client.generate("x")

    assert seen == ["a"]


def test_all_failing_raises_with_details():
    client = FailoverModelClient(
        [Failing(RuntimeError("first")), Failing(RuntimeError("second"))],
        labels=["a", "b"],
    )

    with pytest.raises(RuntimeError, match="Semua model gagal"):
        client.generate("x")


def test_openrouter_402_is_typed(monkeypatch):
    class FakeResponse:
        status_code = 402
        headers = {}

        def json(self):
            return {"error": {"message": "Payment Required"}}

    monkeypatch.setattr(mc.requests, "post", lambda *a, **k: FakeResponse())

    client = OpenRouterClient("tencent/hy-mt2-30b-a3b", api_key="test")

    with pytest.raises(ModelProviderError) as info:
        client.generate("x")

    assert info.value.status_code == 402
    assert info.value.provider == "openrouter"
