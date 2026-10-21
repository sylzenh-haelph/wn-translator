from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.glossary_page import parse_entries, rebuild, safe_glossary

SAMPLE = "# hdr\n## character\nEris = \n# Earth = Tanah\n## item\nExcalibur = Excalibur\n"


def test_parse_marks_disabled_and_sections():
    entries = parse_entries(SAMPLE)
    assert [(e["section"], e["left"], e["active"]) for e in entries] == [
        ("character", "Eris", True),
        ("character", "Earth", False),
        ("item", "Excalibur", True),
    ]


def test_rebuild_changes_only_edited_lines():
    form = {"r2": ["Eris Keren"], "a2": ["on"], "r3": ["Tanah"], "r5": ["Excalibur"], "a5": ["on"]}
    assert rebuild(SAMPLE, form) == [
        "# hdr",
        "## character",
        "Eris = Eris Keren",
        "# Earth = Tanah",
        "## item",
        "Excalibur = Excalibur",
    ]


def test_only_glossary_folder_is_editable():
    with pytest.raises(ValueError):
        safe_glossary("glossary/../x.txt")
    with pytest.raises(ValueError):
        safe_glossary("input/mt_v15.txt")



def test_editor_has_save_button_at_top_and_bottom(tmp_path, monkeypatch):
    import ui.glossary_page as gp

    monkeypatch.setattr(gp, "ROOT", tmp_path)
    (tmp_path / "glossary").mkdir()
    (tmp_path / "glossary" / "x.txt").write_text("Eris = Eris Keren\n", encoding="utf-8")
    page = gp.glossary_page("glossary/x.txt")
    assert page.count("form='gform'") == 1
    assert page.count("type='submit'") >= 2
    assert "Eris Keren" in page
