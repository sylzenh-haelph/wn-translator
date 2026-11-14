from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qa.rule_based_qa import run_qa


def test_quoted_english_title_is_not_flagged():
    src = "Translation note:\nYae Tenzen is a character in the Side Story."
    tr = ("Catatan terjemahan:\n"
          "Yae Tenzen adalah karakter dalam Side Story “Pride and Prejudice”, sebuah cerita sampingan.")
    assert run_qa(src, tr).passed


def test_unquoted_english_is_still_flagged():
    result = run_qa("a\nb", "Ini adalah sebuah kalimat.\nThis is the end of the story and you are not alone.")
    assert any(issue.rule == "untranslated_english" for issue in result.issues)
