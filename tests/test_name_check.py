from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.name_check import check_names


def test_missing_expected_translation_is_flagged():
    chunks = [("chapter_002", "Rudeus walked in.", "Dia masuk.")]
    issues = check_names(chunks, [("Rudeus", "Rudeus Keren")])
    assert issues == [{"chapter": "chapter_002", "kind": "tidak_konsisten", "term": "Rudeus", "expected": "Rudeus Keren"}]


def test_english_term_left_in_translation_is_flagged():
    chunks = [("chapter_002", "Rudeus walked in.", "Rudeus Keren masuk.")]
    issues = check_names(chunks, [("Rudeus", "Rudeus Keren")])
    assert issues == [{"chapter": "chapter_002", "kind": "masih_inggris", "term": "Rudeus", "expected": "Rudeus Keren"}]


def test_identical_translation_is_not_flagged():
    chunks = [("chapter_002", "Rudeus walked in.", "Rudeus masuk.")]
    assert check_names(chunks, [("Rudeus", "Rudeus")]) == []


def test_term_absent_from_source_is_ignored():
    chunks = [("chapter_002", "Nobody came.", "Tidak ada yang datang.")]
    assert check_names(chunks, [("Rudeus", "Rudeus Keren")]) == []


def test_partial_word_is_not_matched():
    chunks = [("chapter_002", "Rudeusian magic.", "Sihir.")]
    assert check_names(chunks, [("Rudeus", "Rudeus Keren")]) == []
