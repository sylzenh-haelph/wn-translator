from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main


class FakeProcessor:
    def process_chapter(self, chapter_id, chunks, **kwargs):
        return [1, 2]


def test_worker_prints_start_and_finish(capsys):
    main._run_worker(FakeProcessor(), "Bab X", chapter_id="c", chunks=[])
    out = capsys.readouterr().out
    assert "mulai: Bab X" in out
    assert "selesai: Bab X | 2 chunk" in out
