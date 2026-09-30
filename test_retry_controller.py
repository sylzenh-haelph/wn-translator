from types import SimpleNamespace

from qa.retry_controller import RetryController
from qa.rule_based_qa import QAIssue
from translation.chapter_context import ContextState


class FakeTranslationEngine:
    def __init__(self):
        self.calls = 0

    def translate(
        self,
        text,
        paragraph_texts,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        self.calls += 1

        new_state = ContextState(
            scene=f"Scene {self.calls}",
            active_characters=["Alice"],
            current_situation=f"Situation {self.calls}",
            references=[f"ref_{self.calls}"],
            style_state={"tone": "natural"},
        )

        return SimpleNamespace(
            translation=f"Translation {self.calls}",
            context_state=new_state,
        )


def qa_function(
    source_text,
    translation,
    preserved_entities=None,
):
    return SimpleNamespace(
        passed=True,
        issues=[],
    )


engine = FakeTranslationEngine()

controller = RetryController(
    translation_engine=engine,
    qa_function=qa_function,
    max_retries=2,
)


chunk = SimpleNamespace(
    chunk_id="chunk_0000",
    text="Alice enters the palace.",
    paragraph_texts=["Alice enters the palace."],
)

chapter_context = SimpleNamespace(
    chapter_id="chapter_001",
    chapter_title="Test",
    character_context={},
    important_references=[],
    style_state={},
)

initial_state = ContextState()


print("=== SUCCESS ===")

result = controller.translate_with_retry(
    chunk=chunk,
    chapter_context=chapter_context,
    context_state=initial_state,
)

print("Translation:", result.translation)
print("Attempts:", result.attempts)
print("Passed:", result.passed)
print("Flagged:", result.flagged)
print("Context:", result.context_state)

assert result.passed is True
assert result.flagged is False
assert len(result.attempts) == 1
assert result.context_state.scene == "Scene 1"
assert result.attempts[0].context_state.scene == "Scene 1"


print("\n=== RETRY CONTEXT PROPAGATION ===")


class RetryTranslationEngine:
    def __init__(self):
        self.calls = 0

    def translate(
        self,
        text,
        paragraph_texts,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        self.calls += 1

        received_scene = context_state.scene

        new_state = ContextState(
            scene=f"Scene after {received_scene or 'initial'}",
            active_characters=["Alice"],
            current_situation="Retry test",
            references=[],
            style_state={},
        )

        return SimpleNamespace(
            translation=f"Translation {self.calls}",
            context_state=new_state,
        )


retry_engine = RetryTranslationEngine()

qa_calls = []


def retry_qa(
    source_text,
    translation,
    preserved_entities=None,
):
    qa_calls.append(translation)

    # Attempt pertama gagal.
    # Attempt kedua berhasil.
    return SimpleNamespace(
        passed=len(qa_calls) >= 2,
        issues=[] if len(qa_calls) >= 2 else [QAIssue(rule="test_failure", message="Intentional test failure")],
    )


retry_controller = RetryController(
    translation_engine=retry_engine,
    qa_function=retry_qa,
    max_retries=2,
)


result = retry_controller.translate_with_retry(
    chunk=chunk,
    chapter_context=chapter_context,
    context_state=ContextState(),
)


print("Attempts:", result.attempts)

for attempt in result.attempts:
    print(
        attempt.attempt_number,
        attempt.translation,
        attempt.context_state.scene,
    )


assert result.passed is True
assert len(result.attempts) == 2

# Attempt kedua harus menerima context
# hasil attempt pertama.
assert result.attempts[1].context_state.scene == (
    "Scene after Scene after initial"
)

assert result.context_state.scene == (
    "Scene after Scene after initial"
)


print("\nPASS")
