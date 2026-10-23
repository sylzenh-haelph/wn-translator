from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.glossary import (
    apply_glossary,
    load_glossary,
    merge_scan_glossary,
    prune_scan_names,
    translate_terms,
)


def test_longest_match_and_word_boundary():
    pairs = [("Dragon God", "Dewa Naga"), ("Dragon God Orsted", "Dewa Naga Orsted")]
    assert apply_glossary("Dragon God Orsted datang.", pairs) == "Dewa Naga Orsted datang."
    assert apply_glossary("Dragon Godly", pairs) == "Dragon Godly"


def test_curly_apostrophe_variant():
    pairs = [("Adventurers’ Guild", "Guild Petualang")]
    assert apply_glossary("Adventurers' Guild", pairs) == "Guild Petualang"


def test_lowercase_term_is_matched():
    pairs = [("Dragon God", "Dewa Naga")]
    assert apply_glossary("dragon god datang.", pairs) == "Dewa Naga datang."


def test_load_skips_comments_and_blank_lines(tmp_path):
    file = tmp_path / "g.txt"
    file.write_text("# komentar\n\n## Bagian\nDragon God = Dewa Naga\n# Earth = Tanah\n", encoding="utf-8")
    assert load_glossary(file) == [("Dragon God", "Dewa Naga")]


def test_merge_scan_keeps_existing_values_and_adds_new(tmp_path):
    out = tmp_path / "g.txt"
    out.write_text("# hdr\n## character\nEris = Eris Keren\n\n## title\n", encoding="utf-8")
    added = merge_scan_glossary(
        [("eris", "character"), ("Rudeus", "character"), ("Dragon God", "title"), ("Excalibur", "item")],
        out,
        "Novel",
    )
    text = out.read_text(encoding="utf-8")
    assert added == 3
    assert "Eris = Eris Keren" in text
    assert text.lower().count("eris =") == 1
    assert "Rudeus =" in text
    assert "Dragon God =" in text
    assert "## item" in text
    assert "Excalibur =" in text


def test_prune_keeps_full_names_only():
    entries = [
        ("Rudeus", "character"),
        ("Rudeus Greyrat", "character"),
        ("rudeus greyrat", "character"),
        ("Dragon God", "title"),
    ]
    kept = prune_scan_names(entries, ["Eris Greyrat"])
    assert kept == [("Rudeus Greyrat", "character"), ("Dragon God", "title")]


def test_prune_skips_names_already_covered_by_glossary():
    assert prune_scan_names([("Greyrat", "character")], ["Rudeus Greyrat"]) == []


def test_merge_fills_translations_for_new_entries(tmp_path):
    out = tmp_path / "g.txt"
    added = merge_scan_glossary(
        [("Dragon God", "title"), ("Excalibur", "item")],
        out,
        "Novel",
        {"dragon god": "Dewa Naga", "excalibur": "Excalibur"},
    )
    text = out.read_text(encoding="utf-8")
    assert added == 2
    assert "Dragon God = Dewa Naga" in text
    assert "Excalibur = Excalibur" in text


class FakeClient:
    def __init__(self, reply):
        self.reply = reply

    def generate(self, prompt):
        return self.reply


class BrokenClient:
    def generate(self, prompt):
        raise RuntimeError("kuota habis")


def test_translate_terms_uses_model_json():
    client = FakeClient('{"Dragon God": "Dewa Naga"}')
    assert translate_terms(client, ["Dragon God"]) == {"dragon god": "Dewa Naga"}


def test_translate_terms_failure_returns_empty():
    assert translate_terms(BrokenClient(), ["Dragon God"]) == {}



def test_disabled_entry_is_not_duplicated_by_next_scan(tmp_path):
    out = tmp_path / "g.txt"
    out.write_text("# Galewind Horse = Kuda Angin Badai\n", encoding="utf-8")
    added = merge_scan_glossary([("Galewind Horse", "character")], out, "Novel")
    assert added == 0
    assert out.read_text(encoding="utf-8").count("Galewind Horse") == 1


def test_scan_marks_new_entries_until_next_scan(tmp_path):
    from translation.glossary import read_meta

    out = tmp_path / "g.txt"
    merge_scan_glossary([("Dragon God", "title")], out, "Novel")
    assert read_meta(out)["new"] == ["Dragon God"]
    merge_scan_glossary([], out, "Novel")
    assert read_meta(out)["new"] == []
    assert "Dragon God" in read_meta(out)["seen"]
