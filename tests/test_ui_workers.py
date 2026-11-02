from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server


def test_workers_two_adds_flag():
    cmd = server.build_command(Path("input/novel.epub"), None, "epub", "novel.txt", "translate", "20260101_0000", workers=2)
    assert "--workers 2" in cmd


def test_default_has_no_workers_flag():
    cmd = server.build_command(Path("input/novel.epub"), None, "epub", "novel.txt", "translate", "20260101_0000")
    assert "--workers" not in cmd


def test_invalid_workers_rejected_before_starting_job():
    with pytest.raises(ValueError):
        server.start_job(Path("input/novel.epub"), None, "epub", "novel.txt", "translate", workers=3)
