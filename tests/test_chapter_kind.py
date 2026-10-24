from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.server import is_matter


def test_book_title_repeated_is_matter():
    title = "Mushoku Tensei: Jobless Reincarnation Vol. 17"
    assert is_matter(title, title) is True


def test_story_chapter_is_not_matter():
    assert is_matter("Chapter 1:The Road to Asura", "Mushoku Tensei: Jobless Reincarnation Vol. 17") is False


def test_extra_chapter_is_story():
    assert is_matter("Extra Chapter:???", "Mushoku Tensei: Jobless Reincarnation Vol. 17") is False


def test_non_story_keywords_are_matter():
    assert is_matter("Colour Gallery", "") is True
    assert is_matter("Afterword", "") is True
    assert is_matter("Table of Contents", "") is True


def test_map_word_inside_other_word_is_not_matter():
    assert is_matter("Mapping the Demon Realm", "") is False


def test_visible_rows_hides_matter_only():
    from ui.server import visible_rows

    book = 'Mushoku Tensei: Jobless Reincarnation Vol. 17'
    rows = [
        {'id': 'chapter_001', 'title': book},
        {'id': 'chapter_002', 'title': 'Chapter 1:The Road to Asura'},
        {'id': 'chapter_017', 'title': 'Colour Gallery'},
        {'id': 'chapter_018', 'title': book},
    ]
    kept = [r['id'] for r in visible_rows(rows, book)]
    assert kept == ['chapter_002']
