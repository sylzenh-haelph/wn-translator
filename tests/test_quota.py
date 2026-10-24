from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server


def test_estimate_counts_selected_chapters_with_retry_margin(monkeypatch):
    monkeypatch.setattr(
        server,
        "chunk_totals_safe",
        lambda input_path, project: {"chapter_002": 5, "chapter_003": 7},
    )
    assert server.estimate_run_calls(Path("input/x.epub"), {2}) == 6


def test_quota_short_when_estimate_exceeds_remaining(monkeypatch):
    monkeypatch.setattr(server, "DAILY_BUDGET", 1500)
    monkeypatch.setattr(server, "usage_today", lambda: {server.PRIMARY_MODEL: 1400})
    estimate, remaining, short = server.quota_status(200)
    assert remaining == 100
    assert short is True


def test_quota_ok_when_enough_budget_left(monkeypatch):
    monkeypatch.setattr(server, "DAILY_BUDGET", 1500)
    monkeypatch.setattr(server, "usage_today", lambda: {})
    _, remaining, short = server.quota_status(200)
    assert remaining == 1500
    assert short is False
