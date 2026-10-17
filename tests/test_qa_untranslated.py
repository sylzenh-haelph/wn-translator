from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from qa.rule_based_qa import run_qa


def rules(result):
    return [issue.rule for issue in result.issues]


def test_untranslated_english_paragraph_is_flagged():
    source = "Alice entered the palace.\nMarcus followed her."

    ok = run_qa(
        source_text=source,
        translation="Alice memasuki istana.\nMarcus mengikutinya.",
    )
    assert "untranslated_english" not in rules(ok)

    bad = run_qa(
        source_text=source,
        translation="Alice memasuki istana.\n\"But please, don't just disappear on me...\"",
    )
    assert "untranslated_english" in rules(bad)


def test_source_echo_arrow_is_flagged():
    result = run_qa(
        source_text="Alice entered the palace.",
        translation="\"Isn't there another option?\" -> \"Apa tidak ada pilihan lain?\"",
    )
    assert "source_echo" in [issue.rule for issue in result.issues]
