from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server


def test_eta_from_stats(tmp_path):
    stats = tmp_path / "stats"
    stats.mkdir()
    (stats / "translation_stats.json").write_text(
        json.dumps({"total_chunks": 10, "completed_chunks": 5, "duration_seconds": 300}),
        encoding="utf-8",
    )
    text = server.eta_text(tmp_path, [])
    assert "perkiraan sisa" in text
    assert "60 detik per chunk" in text


def test_eta_empty_without_stats(tmp_path):
    assert server.eta_text(tmp_path, []) == ""


def test_notify_does_not_crash_without_termux(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("tidak ada termux-notification")

    monkeypatch.setattr(server.subprocess, "run", boom)
    server.notify("judul", "pesan")
