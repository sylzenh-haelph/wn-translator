from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.job_notify as jn
import ui.server as server


def make_forge(project):
    (project / "progress").mkdir(parents=True, exist_ok=True)
    (project / "stats").mkdir(parents=True, exist_ok=True)
    (project / "chapters.json").write_text(json.dumps([
        {"id": "chapter_001", "title": "A"},
        {"id": "chapter_002", "title": "B"},
    ]), encoding="utf-8")
    (project / "progress" / "chapter_001.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")
    (project / "progress" / "chapter_002.json").write_text(json.dumps({"status": "in_progress"}), encoding="utf-8")
    (project / "stats" / "translation_stats.json").write_text(json.dumps({"duration_seconds": 754}), encoding="utf-8")
    return project


def test_forge_success(tmp_path):
    project = make_forge(tmp_path)
    (project / "progress" / "chapter_002.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")
    title, content, high = jn.build_message("translate", 0, project, "ReZero Arc 7", "")
    assert title == "Forge selesai"
    assert "2/2 chapter selesai" in content
    assert "12 mnt" in content
    assert high is False


def test_forge_stuck_chapter_is_flagged(tmp_path):
    project = make_forge(tmp_path)
    title, content, high = jn.build_message("translate", 0, project, "ReZero", "")
    assert title == "Forge selesai, ada chapter gagal"
    assert "1 chapter perlu diulang" in content
    assert high is True


def test_error_exit(tmp_path):
    project = make_forge(tmp_path)
    title, _, high = jn.build_message("translate", 1, project, "ReZero", "")
    assert title == "Forge berhenti dengan error"
    assert high is True


def test_radar_uses_its_own_name(tmp_path):
    (tmp_path / "scan_progress.json").write_text(json.dumps({"total": 5, "done": 5, "finished": True}), encoding="utf-8")
    title, content, _ = jn.build_message("scan", 0, tmp_path, "ReZero", "-")
    assert title == "Radar selesai"
    assert "5/5 chapter dipindai" in content


def test_done_command_uses_mode_aware_notifier():
    cmd = server.build_command(Path("input/novel.epub"), None, "epub", "novel.txt", "translate", "20260101_0000")
    assert "ui.job_notify done translate" in cmd
    assert "Terjemahkan selesai" not in cmd
