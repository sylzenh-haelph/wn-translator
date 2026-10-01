from dataclasses import dataclass, field

from translation.chapter_context import ContextState


@dataclass
class ProcessedChunk:
    chunk_id: str
    translation: str
    paragraph_translations: list[str] = field(
        default_factory=list
    )
    context_state: ContextState = field(
        default_factory=ContextState
    )
    attempts: int = 0
    qa_passed: bool = False
    flagged: bool = False
    issues: list[str] = field(
        default_factory=list
    )
    cache_hit: bool = False


class ChapterProcessor:
    def __init__(
        self,
        retry_controller,
        progress_db,
        translation_engine=None,
        qa_checker=None,
    ):
        self.translation_engine = translation_engine
        self.qa_checker = qa_checker
        self.retry_controller = retry_controller
        self.progress_db = progress_db

    def process_chapter(
        self,
        chapter_id,
        chunks,
        chapter_context,
        initial_context_state,
        entity_resolutions=None,
    ):
        progress = self.progress_db.load(
            chapter_id
        )

        previous_results = (
            self._get_completed_chunks(progress)
        )

        current_state = initial_context_state
        results = []

        for chunk in chunks:
            existing = previous_results.get(
                chunk.chunk_id
            )

            if existing is not None:
                processed = (
                    self._restore_processed_chunk(
                        existing
                    )
                )

                current_state = (
                    processed.context_state
                )

                results.append(processed)
                continue

            processed = self._process_chunk(
                chunk=chunk,
                chapter_context=chapter_context,
                context_state=current_state,
                entity_resolutions=(
                    entity_resolutions or []
                ),
            )

            current_state = (
                processed.context_state
            )

            results.append(processed)

            self.progress_db.save_chunk(
                chapter_id=chapter_id,
                chunk_id=processed.chunk_id,
                translation=processed.translation,
                context_state=(
                    processed.context_state.to_dict()
                ),
                attempts=processed.attempts,
                qa_passed=processed.qa_passed,
                flagged=processed.flagged,
                qa_issues=processed.issues,
                paragraph_translations=(
                    processed.paragraph_translations
                ),
                cache_hit=processed.cache_hit,
            )

        if results and all(
            processed.qa_passed
            for processed in results
        ):
            self.progress_db.mark_completed(
                chapter_id
            )
        else:
            self.progress_db.start_chapter(
                chapter_id
            )

        return results

    @staticmethod
    def _get_completed_chunks(progress):
        chunks_data = progress.get(
            "chunks",
            []
        )

        if isinstance(chunks_data, dict):
            items = []

            for chunk_id, item in chunks_data.items():
                if isinstance(item, dict):
                    normalized = dict(item)
                    normalized.setdefault(
                        "chunk_id",
                        chunk_id,
                    )
                    items.append(normalized)

            return {
                item["chunk_id"]: item
                for item in items
                if item.get("qa_passed") is True
            }

        if isinstance(chunks_data, list):
            return {
                item["chunk_id"]: item
                for item in chunks_data
                if (
                    isinstance(item, dict)
                    and item.get("qa_passed") is True
                    and item.get("chunk_id")
                )
            }

        return {}

    def _process_chunk(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions,
    ):
        result = (
            self.retry_controller.translate_with_retry(
                chunk=chunk,
                chapter_context=chapter_context,
                context_state=context_state,
                entity_resolutions=entity_resolutions,
            )
        )

        translation = str(
            getattr(
                result,
                "translation",
                "",
            )
        )

        new_state = getattr(
            result,
            "context_state",
            context_state,
        )

        flagged = bool(
            getattr(
                result,
                "flagged",
                False,
            )
        )

        qa_result = getattr(
            result,
            "qa_result",
            None,
        )

        qa_passed = bool(
            getattr(
                result,
                "passed",
                getattr(
                    qa_result,
                    "passed",
                    not flagged,
                ),
            )
        )

        issues = list(
            getattr(
                qa_result,
                "issues",
                [],
            )
        )

        attempts = len(
            getattr(
                result,
                "attempts",
                [],
            )
        )

        # Cache HIT memiliki attempts == 0 karena
        # RetryController tidak memanggil translation engine.
        cache_hit = False

        history = getattr(
            result,
            "history",
            [],
        )

        if (
            isinstance(history, list)
            and history
            and history[0].get("source")
            == "cache"
        ):
            cache_hit = True

        if attempts == 0:
            attempts = 1

        paragraph_translations = (
            self._get_paragraph_translations(
                result,
                chunk,
                translation,
            )
        )

        return ProcessedChunk(
            chunk_id=chunk.chunk_id,
            translation=translation,
            paragraph_translations=(
                paragraph_translations
            ),
            context_state=new_state,
            attempts=attempts,
            qa_passed=qa_passed,
            flagged=flagged,
            issues=issues,
            cache_hit=cache_hit,
        )

    @staticmethod
    def _get_paragraph_translations(
        result,
        chunk,
        translation,
    ):
        values = getattr(
            result,
            "paragraph_translations",
            None,
        )

        if values is not None:
            values = list(values)

            expected_count = len(
                getattr(
                    chunk,
                    "paragraph_ids",
                    [chunk.chunk_id],
                )
            )

            if len(values) != expected_count:
                raise ValueError(
                    "Jumlah paragraph_translations "
                    f"tidak sesuai untuk {chunk.chunk_id}."
                )

            return values

        paragraph_texts = getattr(
            chunk,
            "paragraph_texts",
            None,
        )

        if paragraph_texts is not None:
            if len(paragraph_texts) == 1:
                return [translation]

            raise ValueError(
                "Chunk multi-paragraph membutuhkan "
                "paragraph_translations dari RetryController."
            )

        return [translation]

    @staticmethod
    def _restore_processed_chunk(data):
        state_data = data.get(
            "context_state",
            {},
        )

        state = ContextState(
            scene=state_data.get(
                "scene",
                "",
            ),
            active_characters=list(
                state_data.get(
                    "active_characters",
                    [],
                )
            ),
            current_situation=state_data.get(
                "current_situation",
                "",
            ),
            references=list(
                state_data.get(
                    "references",
                    [],
                )
            ),
            style_state=dict(
                state_data.get(
                    "style_state",
                    {},
                )
            ),
        )

        return ProcessedChunk(
            chunk_id=data["chunk_id"],
            translation=data.get(
                "translation",
                "",
            ),
            paragraph_translations=list(
                data.get(
                    "paragraph_translations",
                    [],
                )
            ),
            context_state=state,
            attempts=int(
                data.get(
                    "attempts",
                    0,
                )
            ),
            qa_passed=bool(
                data.get(
                    "qa_passed",
                    False,
                )
            ),
            flagged=bool(
                data.get(
                    "flagged",
                    False,
                )
            ),
            issues=list(
                data.get(
                    "qa_issues",
                    data.get(
                        "issues",
                        [],
                    ),
                )
            ),
            cache_hit=bool(
                data.get(
                    "cache_hit",
                    False,
                )
            ),
        )
