from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.quality_report import check_quality, english_ratio


def test_english_sentence_is_flagged():
    issues = check_quality([("chapter_002", ["x"], ["The man was not there and they were gone."])])
    assert [i["kind"] for i in issues] == ["inggris_lolos"]


def test_indonesian_sentence_is_not_flagged():
    issues = check_quality([("chapter_002", ["x"], ["Pria itu tidak ada di sana dan mereka sudah pergi."])])
    assert issues == []


def test_short_sentence_is_not_flagged():
    assert english_ratio("Ya, the end.") == 0.0


def test_lost_dialog_label_is_flagged():
    issues = check_quality([("chapter_002", ["Subaru: [Halo.]"], ["Halo."])])
    assert [i["kind"] for i in issues] == ["dialog_hilang"]


def test_kept_dialog_label_is_not_flagged():
    issues = check_quality([("chapter_002", ["Subaru: [Halo.]"], ["Subaru: [Halo.]"])])
    assert issues == []


def test_blank_target_is_skipped():
    issues = check_quality([("chapter_002", ["Subaru: [Halo.]"], [""])])
    assert issues == []
