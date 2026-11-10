from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.job_notify as jn
import ui.server as server


def test_send_does_not_crash_without_termux(monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("tidak ada termux-notification")

    monkeypatch.setattr(jn.subprocess, "run", boom)
    jn.send("judul", "pesan")


def test_job_command_calls_mode_aware_notifier():
    cmd = server.build_command(Path("input/novel.epub"), None, "epub", "novel.txt", "translate", "20260101_0000")
    assert "ui.job_notify done translate" in cmd
    assert "temp/ui_job_exit" in cmd
    assert "sleep" not in cmd
    assert "WN_RESEARCH_ENABLED=0 python" not in cmd
