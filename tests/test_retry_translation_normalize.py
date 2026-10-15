from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from qa.retry_controller import RetryController


class FakeEngine:
    def translate(self, **kwargs):
        return SimpleNamespace(
            translation="Paragraf satu.\n\nParagraf dua.",
            context_state=None,
            paragraph_translations=["Paragraf satu.", "Paragraf dua."],
        )


def test_qa_receives_text_joined_from_paragraphs():
    seen = {}

    def qa(source_text, translation, preserved_entities):
        seen["translation"] = translation
        return SimpleNamespace(passed=True, issues=[])

    controller = RetryController(
        translation_engine=FakeEngine(),
        qa_function=qa,
        max_retries=0,
    )
    chunk = SimpleNamespace(text="src", paragraph_texts=["src1", "src2"])
    result = controller.translate_with_retry(
        chunk=chunk,
        chapter_context=None,
        context_state=None,
        entity_resolutions=[],
    )

    assert seen["translation"] == "Paragraf satu.\nParagraf dua."
    assert result.translation == "Paragraf satu.\n\nParagraf dua."
