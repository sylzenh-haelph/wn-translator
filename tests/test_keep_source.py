from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.keep_rules import apply_keep, keep_source


def test_symbol_only_separator_is_kept():
    assert keep_source("△ ▼ △ ▼ △ ▼ △")


def test_url_only_line_is_kept():
    assert keep_source("https://witchculttranslation.com/2022/05/04/arc-7-chapter-60/")


def test_text_is_still_translated():
    assert not keep_source("Source:")
    assert not keep_source("Translation notes:")


def test_apply_keep_restores_source_for_kept_lines():
    sources = ["Hello there.", "△ ▼ △ ▼", "https://a.com/x"]
    model = ["Halo.", "rusak", "rusak lagi"]
    assert apply_keep(sources, model) == ["Halo.", "△ ▼ △ ▼", "https://a.com/x"]


def test_apply_keep_leaves_mismatched_lengths_alone():
    assert apply_keep(["a"], ["x", "y"]) == ["x", "y"]
