from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import chapter_action


class FakeProgress:
    def __init__(self, status):
        self.status = status

    def load(self, chapter_id):
        return {"status": self.status}


class FakeProcessor:
    def __init__(self, status):
        self.progress_db = FakeProgress(status)


def test_chapter_action():
    assert chapter_action(True, FakeProcessor("not_started"), "c") == "translate"
    assert chapter_action(True, FakeProcessor("completed"), "c") == "restore"
    assert chapter_action(False, FakeProcessor("completed"), "c") == "restore"
    assert chapter_action(False, FakeProcessor("in_progress"), "c") == "skip"
    assert chapter_action(False, FakeProcessor("not_started"), "c") == "skip"
