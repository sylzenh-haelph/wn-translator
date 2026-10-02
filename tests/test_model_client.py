from unittest.mock import patch
import pytest
import requests

from translation.model_client import GeminiClient, OpenRouterClient, create_model_client


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data
        self.headers = {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_factory_gemini():
    client = create_model_client("gemini", "test-model", "key")
    assert isinstance(client, GeminiClient)


def test_factory_openrouter():
    client = create_model_client("openrouter", "test-model", "key")
    assert isinstance(client, OpenRouterClient)


def test_factory_unknown_provider():
    with pytest.raises(ValueError):
        create_model_client("unknown", "model", "key")


def test_openrouter_generate():
    response = FakeResponse(data={
        "choices": [{
            "message": {
                "content": '{"ok": true}'
            }
        }]
    })

    with patch(
        "translation.model_client.requests.post",
        return_value=response,
    ) as post:
        client = OpenRouterClient("google/gemini-test", "secret")
        result = client.generate("return JSON")

    assert result == '{"ok": true}'
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer secret"

    payload = post.call_args.kwargs["json"]
    assert payload["model"] == "google/gemini-test"
    assert payload["messages"][0]["content"] == "return JSON"
    assert payload["response_format"] == {"type": "json_object"}


def test_openrouter_retry():
    responses = [
        FakeResponse(429, {"error": {"message": "rate limited"}}),
        FakeResponse(200, {
            "choices": [{
                "message": {
                    "content": '{"ok": true}'
                }
            }]
        }),
    ]

    with patch(
        "translation.model_client.requests.post",
        side_effect=responses,
    ) as post, patch(
        "translation.model_client.time.sleep"
    ):
        client = OpenRouterClient(
            "google/gemini-test",
            "secret",
            max_retries=1,
        )
        assert client.generate("test") == '{"ok": true}'
        assert post.call_count == 2
