from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from research.query_builder import build_adaptive_query


def test_attempt_one_includes_novel_title():
    query = build_adaptive_query(
        "Alice",
        "character",
        novel_title="The Silver Gate",
        attempt=1,
    )

    assert '"The Silver Gate"' in query


def test_without_novel_title_query_is_plain():
    query = build_adaptive_query(
        "Alice",
        "character",
        attempt=1,
    )

    assert query == '"Alice" character'
