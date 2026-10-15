from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from qa.rule_based_qa import run_qa


def test_blank_source_paragraph_allows_blank_translation():
    result = run_qa(
        source_text="Satu.\n\nDua.",
        translation="Satu.\n \nDua.",
        preserved_entities=[],
    )

    assert not [i for i in result.issues if i.rule == "empty_paragraph"]


def test_blank_translation_for_text_source_is_flagged():
    result = run_qa(
        source_text="Satu.\nDua.",
        translation="Satu.\n \n",
        preserved_entities=[],
    )

    assert any(i.rule == "empty_paragraph" for i in result.issues)
