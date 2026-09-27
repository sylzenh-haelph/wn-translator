from dataclasses import dataclass, field

from translation.chapter_context import ContextState


@dataclass
class RetryAttempt:
    attempt_number: int
    translation: str
    context_state: ContextState
    qa_result: object


@dataclass
class RetryResult:
    passed: bool
    translation: str
    attempts: int
    flagged: bool
    qa_result: object
    context_state: ContextState
    history: list[RetryAttempt] = field(default_factory=list)


class RetryController:
    def __init__(
        self,
        translation_engine,
        qa_function,
        max_retries=2,
    ):
        self.translation_engine = translation_engine
        self.qa_function = qa_function
        self.max_retries = max_retries

    def translate_with_retry(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        history = []
        current_state = context_state

        total_attempts = self.max_retries + 1

        for attempt_number in range(
            1,
            total_attempts + 1,
        ):
            result = self.translation_engine.translate(
                chunk=chunk,
                chapter_context=chapter_context,
                context_state=current_state,
                entity_resolutions=entity_resolutions,
            )

            qa_result = self.qa_function(
                source_text=chunk.text,
                translation=result.translation,
                preserved_entities=self._get_preserved_entities(
                    entity_resolutions
                ),
            )

            attempt = RetryAttempt(
                attempt_number=attempt_number,
                translation=result.translation,
                context_state=result.context_state,
                qa_result=qa_result,
            )

            history.append(attempt)

            # Context dari model menjadi context
            # untuk attempt berikutnya.
            current_state = result.context_state

            if qa_result.passed:
                return RetryResult(
                    passed=True,
                    translation=result.translation,
                    attempts=attempt_number,
                    flagged=False,
                    qa_result=qa_result,
                    context_state=result.context_state,
                    history=history,
                )

        final_attempt = history[-1]

        return RetryResult(
            passed=False,
            translation=final_attempt.translation,
            attempts=total_attempts,
            flagged=True,
            qa_result=final_attempt.qa_result,
            context_state=final_attempt.context_state,
            history=history,
        )

    @staticmethod
    def _get_preserved_entities(entity_resolutions):
        preserved = []

        for entity in entity_resolutions or []:
            if hasattr(entity, "__dict__"):
                entity = entity.__dict__

            if not isinstance(entity, dict):
                continue

            text = entity.get("text")
            translation = entity.get("translation")

            # Character name selalu dipertahankan.
            if entity.get("entity_type") == "character":
                if text:
                    preserved.append(text)
                continue

            # Proper noun/entity tanpa translation
            # juga dipertahankan.
            if text and not translation:
                preserved.append(text)

        return preserved
