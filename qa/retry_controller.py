from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from storage.translation_cache import TranslationCache
from translation.chapter_context import ContextState


@dataclass
class RetryAttempt:
    attempt_number: int
    translation: str
    context_state: ContextState
    qa_result: Any
    paragraph_translations: list[str] = field(
        default_factory=list
    )


@dataclass
class RetryResult:
    passed: bool
    translation: str
    attempts: list[RetryAttempt] = field(
        default_factory=list
    )
    flagged: bool = False
    qa_result: Any = None
    context_state: ContextState | None = None
    history: list[dict[str, Any]] = field(
        default_factory=list
    )
    paragraph_translations: list[str] = field(
        default_factory=list
    )


class RetryController:
    def __init__(
        self,
        translation_engine,
        qa_function: Callable,
        max_retries: int = 2,
        cache: TranslationCache | None = None,
        cache_model: str = "",
    ):
        if max_retries < 0:
            raise ValueError(
                "max_retries tidak boleh negatif."
            )

        self.translation_engine = translation_engine
        self.qa_function = qa_function
        self.max_retries = max_retries
        self.cache = cache
        self.cache_model = cache_model

    @staticmethod
    def _context_state_from_value(
        value: Any,
    ) -> ContextState:
        if isinstance(value, ContextState):
            return value

        if isinstance(value, dict):
            return ContextState(
                scene=value.get("scene", ""),
                active_characters=list(
                    value.get("active_characters", [])
                    or []
                ),
                current_situation=value.get(
                    "current_situation",
                    "",
                ),
                references=list(
                    value.get("references", [])
                    or []
                ),
                style_state=dict(
                    value.get("style_state", {})
                    or {}
                ),
            )

        raise ValueError(
            "context_state cache tidak valid."
        )

    def _build_cache_key(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions,
    ) -> str | None:
        if self.cache is None:
            return None

        return self.cache.build_key(
            source_text=chunk.text,
            paragraph_texts=chunk.paragraph_texts,
            chapter_context=chapter_context,
            context_state=context_state,
            entity_resolutions=(
                entity_resolutions or []
            ),
            model=self.cache_model,
        )

    def _get_cached_result(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions,
    ) -> RetryResult | None:
        if self.cache is None:
            return None

        key = self._build_cache_key(
            chunk=chunk,
            chapter_context=chapter_context,
            context_state=context_state,
            entity_resolutions=entity_resolutions,
        )

        if key is None:
            return None

        cached = self.cache.get(key)

        if cached is None:
            return None

        cached_translation = cached.get(
            "translation"
        )

        if not isinstance(
            cached_translation,
            str,
        ) or not cached_translation.strip():
            return None

        cached_paragraphs = cached.get(
            "paragraph_translations",
            [],
        )

        if not isinstance(
            cached_paragraphs,
            list,
        ):
            return None

        try:
            cached_context = (
                self._context_state_from_value(
                    cached.get(
                        "context_state",
                        {},
                    )
                )
            )
        except ValueError:
            return None

        history = [
            {
                "source": "cache",
                "cache_key": key,
                "passed": True,
            }
        ]

        return RetryResult(
            passed=True,
            translation=cached_translation,
            attempts=[],
            flagged=False,
            qa_result=None,
            context_state=cached_context,
            history=history,
            paragraph_translations=list(
                cached_paragraphs
            ),
        )

    def _save_cache(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions,
        translation,
        paragraph_translations,
    ) -> None:
        if self.cache is None:
            return

        key = self._build_cache_key(
            chunk=chunk,
            chapter_context=chapter_context,
            context_state=context_state,
            entity_resolutions=entity_resolutions,
        )

        if key is None:
            return

        self.cache.set(
            key=key,
            translation=translation,
            paragraph_translations=paragraph_translations,
            context_state=context_state,
            metadata={
                "qa": "passed",
            },
        )

    def translate_with_retry(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        entity_resolutions = (
            entity_resolutions or []
        )

        cached_result = self._get_cached_result(
            chunk=chunk,
            chapter_context=chapter_context,
            context_state=context_state,
            entity_resolutions=entity_resolutions,
        )

        if cached_result is not None:
            return cached_result

        attempts = []
        history = []

        for attempt_number in range(
            1,
            self.max_retries + 2,
        ):
            result = self.translation_engine.translate(
                text=chunk.text,
                paragraph_texts=chunk.paragraph_texts,
                chapter_context=chapter_context,
                context_state=context_state,
                entity_resolutions=entity_resolutions,
            )

            translation = result.translation

            new_context_state = (
                result.context_state
            )

            paragraph_translations = list(
                getattr(
                    result,
                    "paragraph_translations",
                    [],
                )
                or []
            )

            preserved_entities = [
                entity
                for entity in entity_resolutions
                if (
                    isinstance(entity, dict)
                    and entity.get("text")
                )
            ]

            qa_result = self.qa_function(
                source_text=chunk.text,
                translation=translation,
                preserved_entities=preserved_entities,
            )

            attempt = RetryAttempt(
                attempt_number=attempt_number,
                translation=translation,
                context_state=new_context_state,
                qa_result=qa_result,
                paragraph_translations=paragraph_translations,
            )

            attempts.append(attempt)

            history.append(
                {
                    "attempt_number": attempt_number,
                    "passed": qa_result.passed,
                    "issues": [
                        {
                            "rule": issue.rule,
                            "message": issue.message,
                            "severity": issue.severity,
                        }
                        for issue in qa_result.issues
                    ],
                }
            )

            if qa_result.passed:
                self._save_cache(
                    chunk=chunk,
                    chapter_context=chapter_context,
                    context_state=context_state,
                    entity_resolutions=entity_resolutions,
                    translation=translation,
                    paragraph_translations=paragraph_translations,
                )

                return RetryResult(
                    passed=True,
                    translation=translation,
                    attempts=attempts,
                    flagged=False,
                    qa_result=qa_result,
                    context_state=new_context_state,
                    history=history,
                    paragraph_translations=paragraph_translations,
                )

            context_state = new_context_state

        final_attempt = attempts[-1]

        return RetryResult(
            passed=False,
            translation=final_attempt.translation,
            attempts=attempts,
            flagged=True,
            qa_result=final_attempt.qa_result,
            context_state=final_attempt.context_state,
            history=history,
            paragraph_translations=(
                final_attempt.paragraph_translations
            ),
        )
