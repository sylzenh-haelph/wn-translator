from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from qa.retry_controller import RetryController
from qa.rule_based_qa import QAIssue, QAResult
from translation.chapter_context import ContextState


class FakeTranslationEngine:
    def __init__(self):
        self.calls = []

    def translate(self, **kwargs):
        self.calls.append(kwargs)

        return SimpleNamespace(
            translation="Terjemahan awal.",
            paragraph_translations=["Terjemahan awal."],
            context_state=ContextState(
                scene="scene-after-translation",
            ),
        )


class FakeRefinementEngine:
    def __init__(self):
        self.calls = []

    def refine(self, **kwargs):
        self.calls.append(kwargs)

        return SimpleNamespace(
            translation="Terjemahan hasil refinement.",
            paragraph_translations=[
                "Terjemahan hasil refinement."
            ],
            context_state=ContextState(
                scene="scene-after-refinement",
            ),
        )


class FakeQA:
    def __init__(self):
        self.calls = []

    def __call__(
        self,
        source_text,
        translation,
        preserved_entities=None,
    ):
        self.calls.append(
            {
                "source_text": source_text,
                "translation": translation,
                "preserved_entities": preserved_entities,
            }
        )

        if translation == "Terjemahan awal.":
            return QAResult(
                passed=False,
                issues=[
                    QAIssue(
                        rule="test_rule",
                        message="Terjemahan perlu diperbaiki.",
                    )
                ],
            )

        return QAResult(
            passed=True,
            issues=[],
        )


class FakeChunk:
    text = "Original text."
    paragraph_texts = ["Original text."]


def test_retry_uses_refinement_engine_after_qa_failure():
    translation_engine = FakeTranslationEngine()
    refinement_engine = FakeRefinementEngine()
    qa = FakeQA()

    controller = RetryController(
        translation_engine=translation_engine,
        refinement_engine=refinement_engine,
        qa_function=qa,
        max_retries=1,
    )

    result = controller.translate_with_retry(
        chunk=FakeChunk(),
        chapter_context={"tone": "fiction"},
        context_state=ContextState(
            scene="initial",
        ),
        entity_resolutions=[],
    )

    assert result.passed is True
    assert result.flagged is False
    assert result.translation == (
        "Terjemahan hasil refinement."
    )

    assert len(translation_engine.calls) == 1
    assert len(refinement_engine.calls) == 1
    assert len(qa.calls) == 2

    refinement_call = refinement_engine.calls[0]

    assert refinement_call["translation"] == (
        "Terjemahan awal."
    )
    assert refinement_call["paragraph_translations"] == [
        "Terjemahan awal."
    ]
    assert refinement_call["context_state"].scene == (
        "scene-after-translation"
    )

    assert len(refinement_call["qa_issues"]) == 1
    assert refinement_call["qa_issues"][0].rule == (
        "test_rule"
    )
    assert refinement_call["qa_issues"][0].message == (
        "Terjemahan perlu diperbaiki."
    )

    assert result.attempts[0].translation == (
        "Terjemahan awal."
    )
    assert result.attempts[1].translation == (
        "Terjemahan hasil refinement."
    )

    assert result.attempts[0].qa_result.passed is False
    assert result.attempts[1].qa_result.passed is True

    assert result.context_state.scene == (
        "scene-after-refinement"
    )


def test_retry_does_not_use_refinement_when_initial_translation_passes():
    translation_engine = FakeTranslationEngine()
    refinement_engine = FakeRefinementEngine()

    def passing_qa(
        source_text,
        translation,
        preserved_entities=None,
    ):
        return QAResult(
            passed=True,
            issues=[],
        )

    controller = RetryController(
        translation_engine=translation_engine,
        refinement_engine=refinement_engine,
        qa_function=passing_qa,
        max_retries=1,
    )

    result = controller.translate_with_retry(
        chunk=FakeChunk(),
        chapter_context={},
        context_state=ContextState(),
        entity_resolutions=[],
    )

    assert result.passed is True
    assert result.translation == "Terjemahan awal."

    assert len(translation_engine.calls) == 1
    assert len(refinement_engine.calls) == 0
    assert len(result.attempts) == 1
