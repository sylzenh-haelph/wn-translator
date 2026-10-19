from pathlib import Path
import json
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.server import project_for, read_chapters, safe_input, start_job


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


def test_paths_from_browser_are_checked():
    with pytest.raises(ValueError):
        safe_input("input/../secret.epub")
    with pytest.raises(ValueError):
        start_job(Path("input/a.epub"), set())
    with pytest.raises(ValueError):
        start_job(Path("input/a.epub"), {0})


def test_project_follows_novel_name():
    assert project_for(Path("input/mt_v15.epub")) == Path("temp/mt_project")
    assert project_for(Path("input/RZxMT_Chapter_1.epub")) == Path("temp/RZxMT_Chapter_1_project")
