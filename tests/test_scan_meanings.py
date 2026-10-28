from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from research.entity_db import EntityDB
from translation.glossary import translate_terms


class FakeClient:
    def __init__(self, reply=None):
        self.reply = reply
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        if self.reply is None:
            raise AssertionError("model tidak boleh dipanggil")
        return self.reply


@pytest.fixture
def series_db(tmp_path, monkeypatch):
    path = tmp_path / "series.json"
    monkeypatch.setenv("WN_SERIES_ENTITIES", str(path))
    return path


def test_research_translation_used_without_model(series_db):
    db = EntityDB(path=series_db)
    db.add(entity_type="character", canonical_name="Rudeus", translation="Rudeus Keren")
    result = translate_terms(FakeClient(reply=None), ["Rudeus"])
    assert result == {"rudeus": "Rudeus Keren"}


def test_web_evidence_is_sent_to_model(series_db):
    db = EntityDB(path=series_db)
    db.add(entity_type="character", canonical_name="Ars", translation=None,
           research=[{"snippet": "Ars is the royal capital of Asura"}])
    client = FakeClient(reply='{"Ars": "Ars"}')
    result = translate_terms(client, ["Ars"])
    assert "BUKTI DARI WEB" in client.prompts[0]
    assert "Ars is the royal capital of Asura" in client.prompts[0]
    assert result == {"ars": "Ars"}


def test_model_only_when_no_database(monkeypatch):
    monkeypatch.delenv("WN_SERIES_ENTITIES", raising=False)
    client = FakeClient(reply='{"Eris": "Eris"}')
    assert translate_terms(client, ["Eris"]) == {"eris": "Eris"}
