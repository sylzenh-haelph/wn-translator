from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.query_builder import build_adaptive_query


def test_attempt_three_ignores_source_text():
    q3 = build_adaptive_query("Alice", "character", novel_title="N", author="A",
                              chapter_context="Source paragraph: long text here", attempt=3)
    q2 = build_adaptive_query("Alice", "character", novel_title="N", author="A", attempt=2)
    assert "long text" not in q3
    assert q3 == q2
