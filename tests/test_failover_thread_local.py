from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.model_failover import FailoverModelClient


class Fake:
    def generate(self, prompt):
        return "ok"


def test_last_used_not_shared_between_threads():
    client = FailoverModelClient([Fake()], labels=["X"])
    client.generate("p")
    seen = {}
    worker = threading.Thread(target=lambda: seen.update(value=client.last_used))
    worker.start()
    worker.join()
    assert client.last_used == "X"
    assert seen["value"] is None
