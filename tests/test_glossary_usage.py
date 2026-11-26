from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.glossary import prune_unused_entries


def test_unused_entry_removed_after_window(tmp_path):
    g = tmp_path / "g.txt"
    g.write_text("Earth = Tanah\nRoxy = Roxy\n", encoding="utf-8")
    chapters = [(f"c{i}", "Roxy talks.") for i in range(25)]
    removed = prune_unused_entries(g, chapters, window=20)
    assert removed == ["Earth"]
    text = g.read_text(encoding="utf-8")
    assert "Earth" not in text
    assert "Roxy = Roxy" in text


def test_entry_kept_within_window(tmp_path):
    g = tmp_path / "g.txt"
    g.write_text("Earth = Tanah\n", encoding="utf-8")
    chapters = [(f"c{i}", "nothing here") for i in range(5)]
    assert prune_unused_entries(g, chapters, window=20) == []
    assert "Earth = Tanah" in g.read_text(encoding="utf-8")


def test_same_chapter_not_counted_twice(tmp_path):
    g = tmp_path / "g.txt"
    g.write_text("Earth = Tanah\n", encoding="utf-8")
    chapters = [("c0", "nothing here")]
    for _ in range(30):
        prune_unused_entries(g, chapters, window=20)
    assert "Earth = Tanah" in g.read_text(encoding="utf-8")
