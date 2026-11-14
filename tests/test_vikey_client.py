from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import translation.model_client as mc
from config.settings import AppConfig


class FakeResp:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body
        self.headers = {}

    def json(self):
        return self._body


def test_vikey_client_reads_choice_text(monkeypatch):
    seen = {}

    def fake_post(self, url, headers=None, json=None, timeout=None):
        seen["url"] = url
        seen["auth"] = headers["Authorization"]
        seen["model"] = json["model"]
        return FakeResp(200, {"choices": [{"message": {"content": "halo"}}]})

    monkeypatch.setattr(mc.requests.Session, "post", fake_post)
    client = mc.create_model_client(provider="vikey", model="deepseek-v4-flash", api_key="k", max_retries=0)
    assert client.generate("x") == "halo"
    assert seen["url"] == "https://api.vikey.ai/v1/chat/completions"
    assert seen["auth"] == "Bearer k"
    assert seen["model"] == "deepseek-v4-flash"


def test_vikey_key_from_env_and_config_validates(monkeypatch):
    monkeypatch.setenv("VIKEY_API_KEY", "abc")
    cfg = AppConfig(translation_provider="vikey", translation_model="deepseek-v4-flash", translation_fallbacks="")
    assert cfg.get_api_key("vikey") == "abc"
    cfg.validate()
