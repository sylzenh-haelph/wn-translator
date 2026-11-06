from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server

LOG = """[1/14] Chapter: Chapter 1:Ujian
  Processed : 8 chunks
[7/14] Chapter: Chapter 7:Library Labyrinth
  WARNING: Translasi gagal di gemini:gemma-4-31b-it, pindah ke cadangan.
  WARNING: terjemahan chapter gagal, chapter dibiarkan asli: Jumlah paragraph_translations tidak sesuai: 35 != 36
"""


def test_chapter_reasons_collect_warnings_per_chapter():
    reasons = server.chapter_reasons(LOG)
    assert "Chapter 1:Ujian" not in reasons
    info = reasons["Chapter 7:Library Labyrinth"]
    assert info["count"] == 2
    assert any("35 != 36" in line for line in info["lines"])


def test_failed_block_lists_only_stopped_in_progress_chapters():
    rows = [
        {"id": "chapter_001", "title": "Chapter 1:Ujian", "status": "completed", "done": 8, "total": 8},
        {"id": "chapter_008", "title": "Chapter 7:Library Labyrinth", "status": "in_progress", "done": 14, "total": 16},
    ]
    markup = server.failed_block(rows, False, LOG)
    assert "Chapter 7:Library Labyrinth" in markup
    assert "Chapter 1:Ujian" not in markup
    assert "14/16 chunk selesai" in markup


def test_failed_block_hidden_while_running():
    rows = [{"id": "chapter_008", "title": "Chapter 7:Library Labyrinth", "status": "in_progress", "done": 1, "total": 2}]
    assert server.failed_block(rows, True, LOG) == ""
