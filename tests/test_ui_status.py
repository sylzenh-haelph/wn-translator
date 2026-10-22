from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.server import (
    build_command,
    chapter_files,
    clean_output_name,
    disposition,
    download_name,
    progress_summary,
    project_for,
    read_chapters,
    resolve_glossary,
    safe_input,
    scan_bar,
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


def test_scan_bar_shows_chapter_progress():
    markup = scan_bar({"total": 4, "done": 1, "current": "Bab A", "finished": False})
    assert "1/4 chapter (25%)" in markup
    assert "Sedang: Bab A" in markup


def test_download_name_has_novel_title_and_chapter_number():
    assert download_name("temp/Tidak Ada_chapters/chapter-03.epub", Path("x.epub")) == "Tidak Ada - Chapter 03.epub"
    assert download_name("temp/mt_v15.epub", Path("temp/mt_v15.epub")) == "mt_v15.epub"


def test_disposition_is_latin1_safe():
    header = disposition("Bab ’3’.epub")
    header.encode("latin-1")
    assert "filename*=UTF-8''" in header


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
    with pytest.raises(ValueError):
        start_job(Path("input/a.epub"), None, "epub", "a.txt", "translate", "../x")


def test_clean_output_name():
    assert clean_output_name("") == ""
    assert clean_output_name("Bab 3.epub") == "Bab 3"
    assert clean_output_name("RZxMT (final)") == "RZxMT (final)"
    for bad in ["../x", "a/b", ".hidden", "x" * 81, "a;rm"]:
        with pytest.raises(ValueError):
            clean_output_name(bad)


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


def test_build_command_uses_custom_output_name():
    cmd = build_command(Path("input/novel.epub"), None, "docx", "novel.txt", "translate", "20260101_0000", "Bab 3")
    assert "temp/Bab 3.docx" in cmd


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



def test_render_log_splits_sessions(tmp_path, monkeypatch):
    import ui.server as server

    log = tmp_path / "job.log"
    log.write_text(
        "a\n===== MULAI terjemahan · x · EPUB · 01-01 00:00 =====\nb\n===== DIHENTIKAN · 01-01 00:05 =====\nc\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(server, "JOB_LOG", log)
    markup = server.render_log()
    assert markup.count("class='sess'") == 2
    assert "<pre>a</pre>" in markup



def test_chunk_hint_points_to_latest_active_chapter(tmp_path):
    import os
    from ui.server import chunk_hint

    (tmp_path / "progress").mkdir()
    old = tmp_path / "progress" / "chapter_002.json"
    new = tmp_path / "progress" / "chapter_003.json"
    old.write_text("{}", encoding="utf-8")
    new.write_text("{}", encoding="utf-8")
    os.utime(old, (1000, 1000))
    os.utime(new, (2000, 2000))
    rows = [
        {"id": "chapter_002", "title": "Lama", "status": "in_progress", "done": 1, "total": 8},
        {"id": "chapter_003", "title": "Baru", "status": "in_progress", "done": 2, "total": 8},
    ]
    markup = chunk_hint(rows, True, tmp_path)
    assert "Baru" in markup
    assert "chunk 3/8" in markup
    assert chunk_hint(rows, False, tmp_path) == ""



def test_progress_summary_uses_all_chapter_totals():
    from ui.server import progress_summary

    rows = [
        {"id": "chapter_002", "title": "A", "status": "completed", "done": 4, "total": 4},
        {"id": "chapter_003", "title": "B", "status": "not_started", "done": 0, "total": 0},
    ]
    s = progress_summary(rows, {"chapter_002": 4, "chapter_003": 6})
    assert (s["done"], s["total"], s["percent"]) == (4, 10, 40)


def test_chunk_totals_reads_cached_file(tmp_path):
    from ui.server import chunk_totals

    (tmp_path / "chunk_totals.json").write_text('{"chapter_002": 5}', encoding="utf-8")
    assert chunk_totals(Path("input/x.epub"), tmp_path) == {"chapter_002": 5}


def test_build_command_stops_without_sleep():
    cmd = build_command(Path("input/novel.epub"), None, "epub", "novel.txt", "translate", "20260101_0000")
    assert "sleep" not in cmd
    assert "SELESAI" in cmd


def test_build_command_can_skip_research():
    cmd = build_command(Path("input/novel.epub"), None, "epub", "novel.txt", "translate", "20260101_0000", "", True)
    assert "WN_RESEARCH_ENABLED=0 python" in cmd
