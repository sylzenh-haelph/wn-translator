from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.research_provider import ResearchResult
from research.voice_research import collect_characters, filter_speakers, research_voices, voice_query
from translation.voice_profiles import load_voice_profiles, voice_section


class FakeProvider:
    def __init__(self):
        self.queries = []

    def search(self, query, max_results=5):
        self.queries.append(query)
        return [ResearchResult(title="Wiki", url="https://example.com", snippet="Speaks politely and formally.")]


class FakeClient:
    def __init__(self, reply):
        self.reply = reply

    def generate(self, prompt):
        return self.reply


def test_voice_section_only_for_names_in_text(tmp_path, monkeypatch):
    file = tmp_path / "v.json"
    file.write_text(json.dumps({
        "Rudeus Greyrat": {"voice": "formal, memakai saya", "checked": True},
        "Eris": {"voice": "", "checked": True},
    }), encoding="utf-8")
    monkeypatch.setenv("WN_VOICE_FILE", str(file))
    section = voice_section(["Rudeus Greyrat walked in."])
    assert "Rudeus Greyrat: formal, memakai saya" in section
    assert "Eris" not in section
    assert voice_section(["Nothing here."]) == ""


def test_voice_section_empty_without_env(monkeypatch):
    monkeypatch.delenv("WN_VOICE_FILE", raising=False)
    assert voice_section(["Rudeus"]) == ""


def test_collect_characters_reads_entity_structures():
    data = {
        "entities": [
            {"text": "Rudeus Greyrat", "entity_type": "character"},
            {"text": "Orsted", "entity_type": "character"},
            {"text": "Ruijerd figurines", "entity_type": "item"},
        ],
        "other": {"Eris": {"entity_type": "character"}},
    }
    assert collect_characters(data) == ["Rudeus Greyrat", "Orsted", "Eris"]


def test_speaker_label_counts_as_dialogue():
    paragraphs = ["Subaru: [Hello there.]", "Subaru: [Bye.]"]
    kept, dropped = filter_speakers(["Subaru"], paragraphs)
    assert kept == ["Subaru"]
    assert dropped == []


def test_full_name_matches_speaker_label():
    paragraphs = ["Subaru: [Hi.]"]
    kept, _ = filter_speakers(["Subaru Natsuki"], paragraphs)
    assert kept == ["Subaru Natsuki"]


def test_untagged_novel_keeps_frequent_quoted_speakers():
    paragraphs = ['"Rudeus, come here," she said.'] * 5
    kept, _ = filter_speakers(["Rudeus"], paragraphs)
    assert kept == ["Rudeus"]


def test_narration_only_is_dropped():
    paragraphs = ["Orsted was mentioned in the book.", '"Hm," Eris said.']
    kept, dropped = filter_speakers(["Orsted", "Eris"], paragraphs)
    assert kept == []
    assert dropped == ["Orsted", "Eris"]


def test_research_voices_caches_results(tmp_path):
    path = tmp_path / "v.json"
    provider = FakeProvider()
    client = FakeClient('{"voice": "formal"}')
    assert research_voices(["Rudeus"], provider, client, path, "Mushoku") == 1
    assert provider.queries == [voice_query("Rudeus", "Mushoku")]
    research_voices(["Rudeus"], provider, client, path, "Mushoku")
    assert len(provider.queries) == 1


def test_empty_summary_is_cached_as_checked(tmp_path):
    path = tmp_path / "v.json"
    provider = FakeProvider()
    client = FakeClient('{"voice": ""}')
    research_voices(["Eris"], provider, client, path)
    assert load_voice_profiles(path)["Eris"] == {"voice": "", "checked": True}
