from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation import model_client


def test_counts_per_model_per_day(tmp_path, monkeypatch):
    file = tmp_path / "usage.json"
    monkeypatch.setenv("WN_USAGE_FILE", str(file))
    model_client._count_request("m1")
    model_client._count_request("m1")
    model_client._count_request("m2")
    data = json.loads(file.read_text(encoding="utf-8"))
    day = list(data.values())[0]
    assert day == {"m1": 2, "m2": 1}


def test_no_file_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv("WN_USAGE_FILE", raising=False)
    model_client._count_request("m1")
    assert not any(tmp_path.iterdir())
