from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.chapter_title_translator import ChapterTitleTranslator


class CountingClient:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt):
        self.calls += 1
        return '{"title": "Chapter 1: The Gate (Gerbang)"}'


def test_title_is_cached_when_env_set(tmp_path, monkeypatch):
    monkeypatch.setenv("WN_TITLE_CACHE", str(tmp_path / "titles.json"))
    client = CountingClient()
    translator = ChapterTitleTranslator(client)
    assert translator.translate("Chapter 1: The Gate") == "Chapter 1: The Gate (Gerbang)"
    assert translator.translate("Chapter 1: The Gate") == "Chapter 1: The Gate (Gerbang)"
    assert client.calls == 1


def test_no_cache_without_env(monkeypatch):
    monkeypatch.delenv("WN_TITLE_CACHE", raising=False)
    client = CountingClient()
    translator = ChapterTitleTranslator(client)
    translator.translate("Chapter 1: The Gate")
    translator.translate("Chapter 1: The Gate")
    assert client.calls == 2
