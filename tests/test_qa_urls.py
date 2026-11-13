from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qa.rule_based_qa import run_qa


def test_url_with_english_words_is_not_untranslated():
    url = "https://witchculttranslation.com/2022/05/04/arc-7-chapter-60-the-planting-of-a-tumultuous-seedling"
    result = run_qa(f"Source:\n{url}", f"Sumber:\n{url}")
    assert result.passed


def test_real_english_sentence_still_flagged():
    result = run_qa("a\nb", "Ini adalah sebuah kalimat.\nThis is the end of the story and you are not alone.")
    assert any(issue.rule == "untranslated_english" for issue in result.issues)
