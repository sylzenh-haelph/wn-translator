from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import full_output_blocked


def test_no_blockers_when_everything_ok():
    assert full_output_blocked([], 0) == []


def test_failed_chapter_blocks_full_output():
    assert full_output_blocked(["chapter_008"], 0) == ["chapter gagal: chapter_008"]


def test_flagged_chunk_blocks_full_output():
    assert full_output_blocked([], 2) == ["chunk flagged: 2"]


def test_duplicate_failed_chapter_listed_once():
    assert full_output_blocked(["chapter_001", "chapter_001"], 0) == ["chapter gagal: chapter_001"]
