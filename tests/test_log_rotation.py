from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server


def test_rotate_moves_current_log_to_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "JOB_LOG", tmp_path / "temp" / "ui_job.log")
    server.JOB_LOG.parent.mkdir(parents=True)
    server.JOB_LOG.write_text("isi lama\n", encoding="utf-8")
    moved = server.rotate_job_log()
    assert moved is not None
    assert moved.read_text(encoding="utf-8") == "isi lama\n"
    assert not server.JOB_LOG.exists()


def test_rotate_keeps_only_latest_archives(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "JOB_LOG", tmp_path / "temp" / "ui_job.log")
    archive = tmp_path / "temp" / "logs"
    archive.mkdir(parents=True)
    for number in range(25):
        (archive / f"2026{number:04d}_000000.log").write_text("x", encoding="utf-8")
    server.JOB_LOG.write_text("baru\n", encoding="utf-8")
    server.rotate_job_log(keep=20)
    assert len(list(archive.glob("*.log"))) == 20


def test_rotate_skips_empty_or_missing_log(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "ROOT", tmp_path)
    monkeypatch.setattr(server, "JOB_LOG", tmp_path / "temp" / "ui_job.log")
    assert server.rotate_job_log() is None
    server.JOB_LOG.parent.mkdir(parents=True)
    server.JOB_LOG.write_text("", encoding="utf-8")
    assert server.rotate_job_log() is None
