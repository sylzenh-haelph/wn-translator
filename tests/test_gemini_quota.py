from translation import model_client
from translation.model_client import GeminiClient, ModelProviderError
import pytest


class Resp:
    def __init__(self, status, data):
        self.status_code = status
        self.headers = {}
        self._data = data

    def json(self):
        return self._data


def no_sleep(seconds):
    raise AssertionError("tidak boleh menunggu untuk kuota harian")


def test_daily_quota_is_not_retried(monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return Resp(429, {"error": {"message": "Quota exceeded for GenerateRequestsPerDayPerProjectPerModel"}})

    monkeypatch.setattr(model_client.requests, "post", fake_post)
    monkeypatch.setattr(model_client.time, "sleep", no_sleep)
    client = GeminiClient(api_key="x", max_retries=3)
    with pytest.raises(ModelProviderError):
        client.generate("halo")
    assert len(calls) == 1


def test_per_minute_limit_still_retries(monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return Resp(429, {"error": {"message": "Quota exceeded per minute"}})
        return Resp(200, {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    monkeypatch.setattr(model_client.requests, "post", fake_post)
    monkeypatch.setattr(model_client.time, "sleep", lambda seconds: None)
    client = GeminiClient(api_key="x", max_retries=3)
    assert client.generate("halo") == "{}"
    assert len(calls) == 2
