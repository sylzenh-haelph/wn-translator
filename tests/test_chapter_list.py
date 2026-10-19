from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import parse_chapter_list


def test_single_range_and_list():
    assert parse_chapter_list("3") == {3}
    assert parse_chapter_list("2-4") == {2, 3, 4}
    assert parse_chapter_list("2,5,7-8") == {2, 5, 7, 8}


def test_invalid_values_are_rejected():
    for bad in ["0", "5-2", "a", "2-", "1-2-3", "2,,x"]:
        with pytest.raises(ValueError):
            parse_chapter_list(bad)
