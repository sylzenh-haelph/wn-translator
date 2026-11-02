from pathlib import Path
import json
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import translation.model_client as mc


def test_usage_counts_are_not_lost(tmp_path, monkeypatch):
    usage = tmp_path / "usage.json"
    monkeypatch.setenv("WN_USAGE_FILE", str(usage))

    def work():
        for _ in range(20):
            mc._count_request("m")

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    data = json.loads(usage.read_text(encoding="utf-8"))
    day = list(data.values())[0]
    assert day["m"] == 160
