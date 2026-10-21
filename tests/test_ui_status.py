from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.server import (
    build_command,
    chapter_files,
    progress_summary,
    project_for,
    read_chapters,
    resolve_glossary,
    safe_input,
    start_job,
)


def test_read_chapters_reads_progress(tmp_path):
    (tmp_path / "progress").mkdir()
    (tmp_path / "chapters.json").write_text(
        json.dumps([{"id": "chapter_001", "title": "A"}, {"id": "chapter_002", "title": "B"}]),
        encoding="utf-8",
    )
    (tmp_path / "progress" / "chapter_001.json").write_text(
        json.dumps({"status": "completed", "chunks": {"c0": {"qa_passed": True}, "c1": {"qa_passed": True}}}),
        encoding="utf-8",
    )
    rows = read_chapters(tmp_path)
    assert rows[0] == {"id": "chapter_001", "title": "A", "status": "completed", "done": 2, "total": 2}
    assert rows[1]["status"] == "not_started"


def test_progress_summary_counts_chunks_and_chapters():
    rows = [
        {"title": "A", "status": "completed", "done": 4, "total": 4},
        {"title": "B", "status": "in_progress", "done": 1, "total": 4},
        {"title": "C", "status": "not_started", "done": 0, "total": 0},
    ]
    s = progress_summary(rows)
    assert (s["done"], s["total"], s["percent"]) == (5, 8, 62)
    assert (s["finished"], s["chapters"], s["current"]) == (1, 3, "B")
    assert progress_summary([])["percent"] == 0


def test_paths_from_browser_are_checked():
    with pytest.raises(ValueError):
        safe_input("input/../secret.epub")
    with pytest.raises(ValueError):
        safe_input("input/novel.pdf")
    with pytest.raises(ValueError):
        start_job(Path("input/a.epub"), set(), "epub", "a.txt", "translate")
    with pytest.raises(ValueError):
        start_job(Path("input/a.epub"), None, "pdf", "a.txt", "translate")
    with pytest.raises(ValueError):
        start_job(Path("input/a.epub"), None, "epub", "a.txt", "export")


def test_build_command_for_scan_translate_and_export():
    scan = build_command(Path("input/novel.epub"), None, "epub", "novel.txt", "scan", "20260101_0000")
    assert "--scan-glossary" in scan
    assert " -o " not in scan
    tl = build_command(Path("input/novel.docx"), {1}, "docx", "novel.txt", "translate", "20260101_0000")
    assert "temp/novel_ui_20260101_0000.docx" in tl
    assert "--chapter 1" in tl
    assert "--glossary" in tl
    assert "--export-only" not in tl
    ex = build_command(Path("input/novel.epub"), {2, 3}, "epub", "novel.txt", "export", "20260101_0000")
    assert "--export-only" in ex
    assert "--chapter 2,3" in ex


def test_chapter_files_lists_each_format():
    exports = {
        "temp/x_chapters/chapter-02.epub": Path("a"),
        "temp/x_chapters/chapter-02.docx": Path("b"),
        "temp/x_chapters/chapter-03.epub": Path("c"),
    }
    assert chapter_files("x", 2, exports) == {
        "epub": "temp/x_chapters/chapter-02.epub",
        "docx": "temp/x_chapters/chapter-02.docx",
    }
    assert chapter_files("x", 3, exports) == {"epub": "temp/x_chapters/chapter-03.epub"}
    assert chapter_files("x", 4, exports) == {}


def test_resolve_glossary_names():
    assert resolve_glossary("__new__", "novel_baru") == "novel_baru.txt"
    with pytest.raises(ValueError):
        resolve_glossary("__new__", "a b")
    with pytest.raises(ValueError):
        resolve_glossary("tidak_ada.txt", "")


def test_project_follows_novel_name():
    assert project_for(Path("input/mt_v15.epub")) == Path("temp/mt_project")
    assert project_for(Path("input/RZxMT_Chapter_1.docx")) == Path("temp/RZxMT_Chapter_1_project")
