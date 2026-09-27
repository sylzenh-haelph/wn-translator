from dataclasses import dataclass, field
from typing import Any

from models.document import Document
from models.document import Paragraph

from translation.chapter_context import (
    ContextState,
    build_chapter_context,
)
from translation.chapter_processor import ChapterProcessor
from translation.chapter_splitter import DocumentChapterSplitter
from translation.chunker import build_chunks


@dataclass
class ChapterInput:
    chapter_id: str
    paragraphs: list
    chapter_title: str = ""
    heading: Paragraph | None = None
    resolved_entities: list = field(
        default_factory=list
    )
    character_context: dict[str, Any] = field(
        default_factory=dict
    )
    style_state: dict[str, Any] = field(
        default_factory=dict
    )
    important_references: list = field(
        default_factory=list
    )


@dataclass
class ChapterResult:
    chapter_id: str
    chunk_count: int
    processed_chunks: list
    status: str
    heading: Paragraph | None = None
    entity_count: int = 0
    resolved_entities: list = field(
        default_factory=list
    )


@dataclass
class DocumentResult:
    title: str
    author: str
    chapter_count: int
    chapters: list


class TranslationOrchestrator:
    def __init__(
        self,
        chapter_processor: ChapterProcessor,
        max_tokens=1000,
        chapter_splitter=None,
        entity_service=None,
    ):
        self.chapter_processor = chapter_processor
        self.max_tokens = max_tokens

        self.chapter_splitter = (
            chapter_splitter
            or DocumentChapterSplitter()
        )

        self.entity_service = entity_service

    def _set_document_metadata(
        self,
        document: Document,
    ):
        """
        Memberikan metadata dokumen ke ChapterEntityService.
        """

        if self.entity_service is None:
            return

        if hasattr(
            self.entity_service,
            "document_title",
        ):
            self.entity_service.document_title = (
                document.title or ""
            )

        if hasattr(
            self.entity_service,
            "author",
        ):
            self.entity_service.author = (
                document.author or ""
            )

    def process_chapter(
        self,
        chapter_input: ChapterInput,
    ):
        # --------------------------------------------------
        # ENTITY PIPELINE
        # --------------------------------------------------

        resolved_entities = list(
            chapter_input.resolved_entities
        )

        if (
            self.entity_service is not None
            and not resolved_entities
        ):
            entity_result = (
                self.entity_service.process_chapter(
                    chapter_id=chapter_input.chapter_id,
                    paragraphs=chapter_input.paragraphs,
                )
            )

            resolved_entities = (
                entity_result.entities
            )

        # --------------------------------------------------
        # CHAPTER CONTEXT
        # --------------------------------------------------

        chapter_context = build_chapter_context(
            chapter_id=chapter_input.chapter_id,
            chapter_title=chapter_input.chapter_title,
            resolved_entities=resolved_entities,
            character_context=(
                chapter_input.character_context
            ),
            style_state=chapter_input.style_state,
            important_references=(
                chapter_input.important_references
            ),
        )

        # --------------------------------------------------
        # CHUNKING
        # --------------------------------------------------

        chunks = build_chunks(
            chapter_input.paragraphs,
            max_tokens=self.max_tokens,
        )

        # --------------------------------------------------
        # TRANSLATION
        # --------------------------------------------------

        initial_context_state = ContextState()

        processed_chunks = (
            self.chapter_processor.process_chapter(
                chapter_id=chapter_input.chapter_id,
                chunks=chunks,
                chapter_context=chapter_context,
                initial_context_state=(
                    initial_context_state
                ),
                entity_resolutions=resolved_entities,
            )
        )

        # --------------------------------------------------
        # RESULT
        # --------------------------------------------------

        progress = (
            self.chapter_processor.progress_db.load(
                chapter_input.chapter_id
            )
        )

        return ChapterResult(
            chapter_id=chapter_input.chapter_id,
            chunk_count=len(chunks),
            processed_chunks=processed_chunks,
            status=progress["status"],
            heading=chapter_input.heading,
            entity_count=len(resolved_entities),
            resolved_entities=resolved_entities,
        )

    def process_document(
        self,
        document: Document,
    ):
        # --------------------------------------------------
        # DOCUMENT METADATA → ENTITY SERVICE
        # --------------------------------------------------

        self._set_document_metadata(document)

        # --------------------------------------------------
        # CHAPTER SPLITTING
        # --------------------------------------------------

        chapters = self.chapter_splitter.split(
            document
        )

        results = []

        # --------------------------------------------------
        # CHAPTER-BY-CHAPTER PROCESSING
        # --------------------------------------------------

        for chapter in chapters:
            chapter_input = ChapterInput(
                chapter_id=chapter.chapter_id,
                paragraphs=chapter.paragraphs,
                chapter_title=chapter.title,
                heading=chapter.heading,
            )

            result = self.process_chapter(
                chapter_input
            )

            results.append(result)

        return DocumentResult(
            title=document.title,
            author=document.author,
            chapter_count=len(chapters),
            chapters=results,
        )
