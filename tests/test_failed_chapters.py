from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ui.server as server

LOG = """
===== MULAI translate · x · EPUB · 01-01 00:00 =====
[1/2] Chapter: Chapter 1:Ujian
  Processed : 8 chunks
[2/2] Chapter: Chapter 7:Library Labyrinth
  WARNING: Translasi gagal di gemini:gemma-4-31b-it, pindah ke cadangan.
  WARNING: terjemahan chapter gagal, chapter dibiarkan asli: Jumlah paragraph_translations tidak sesuai: 35 != 36
"""


def test_chapter_reasons_picks_last_warning_per_chapter():
    reasons = server.chapter_reasons(LOG)
    assert "Chapter 1:Ujian" not in reasons
    assert "35 != 36" in reasons["Chapter 7:Library Labyrinth"]


def test_failed_block_lists_only_stopped_in_progress_chapters():
    rows = [
        {"id": "chapter_001", "title": "Chapter 1:Ujian", "status": "completed", "done": 8, "total": 8},
        {"id": "chapter_008", "title": "Chapter 7:Library Labyrinth", "status": "in_progress", "done": 14, "total": 16},
    ]
    markup = server.failed_block(rows, False, LOG, "input/x.epub", "x.txt", "epub")
    assert "Chapter 7:Library Labyrinth" in markup
    assert "Chapter 1:Ujian" not in markup
    assert "name='ch' value='chapter_008'" in markup


def test_failed_block_hidden_while_running():
    rows = [{"id": "chapter_008", "title": "Chapter 7:Library Labyrinth", "status": "in_progress", "done": 1, "total": 2}]
    assert server.failed_block(rows, True, LOG, "input/x.epub", "x.txt", "epub") == ""
