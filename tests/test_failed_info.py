from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server

LOG = """[5/14] Chapter: Chapter 3: Foo
  WARNING: Translasi gagal di gemini:x, pindah. Penyebab: HTTP 500
  WARNING: terjemahan chapter gagal, chapter dibiarkan asli: Semua model gagal
[6/14] Chapter: Chapter 4
  Processed : 3 chunks
"""


def test_chapter_reasons_collect_all_warnings():
    found = server.chapter_reasons(LOG)
    assert found["Chapter 3: Foo"]["count"] == 2
    assert "Chapter 4" not in found


def test_failed_block_has_no_retry_button_and_shows_progress():
    rows = [{"id": "chapter_003", "title": "Chapter 3: Foo", "status": "in_progress", "done": 2, "total": 5}]
    out = server.failed_block(rows, False, LOG)
    assert "Ulang chapter ini" not in out
    assert "2/5 chunk selesai" in out
    assert "peringatan tercatat: 2" in out
