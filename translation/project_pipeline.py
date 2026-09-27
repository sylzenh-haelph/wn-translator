from dataclasses import dataclass, field
from pathlib import Path

from models.document import Document
from storage.progress_db import ProgressDB
from translation.chapter_context import (
    build_chapter_context,
    build_initial_context_state,
)
from translation.chapter_splitter import (
    DocumentChapter,
    DocumentChapterSplitter,
)
from translation.chunker import build_chunks


@dataclass
class ProjectConfig:
    project_dir: Path
    source_path: Path
    output_path: Path
    output_format: str
    progress_dir: Path | None = None

    def __post_init__(self):
        self.project_dir = Path(self.project_dir)
        self.source_path = Path(self.source_path)
        self.output_path = Path(self.output_path)

        if self.progress_dir is None:
            self.progress_dir = self.project_dir / "progress"
        else:
            self.progress_dir = Path(self.progress_dir)

        self.output_format = self.output_format.lower()

        if self.output_format not in {"epub", "docx"}:
            raise ValueError(
                "output_format harus 'epub' atau 'docx'."
            )


@dataclass
class ProjectState:
    project_id: str
    source_path: str
    output_path: str
    output_format: str
    chapter_ids: list[str] = field(default_factory=list)
    completed_chapters: list[str] = field(default_factory=list)
    current_chapter_id: str | None = None
    status: str = "not_started"


class ProjectPipeline:
    """
    Project-level orchestration.

    Mengatur lifecycle proyek dan menghubungkan:
    chapter splitter → chunker → chapter context
    → ChapterProcessor → progress tracking.
    """

    def __init__(
        self,
        config: ProjectConfig,
        splitter=None,
        progress_db=None,
        chapter_processor=None,
        chunk_builder=None,
        context_builder=None,
        initial_context_builder=None,
    ):
        self.config = config

        self.splitter = (
            splitter
            if splitter is not None
            else DocumentChapterSplitter()
        )

        self.progress_db = (
            progress_db
            if progress_db is not None
            else ProgressDB(config.progress_dir)
        )

        self.chapter_processor = chapter_processor

        self.chunk_builder = (
            chunk_builder
            if chunk_builder is not None
            else build_chunks
        )

        self.context_builder = (
            context_builder
            if context_builder is not None
            else build_chapter_context
        )

        self.initial_context_builder = (
            initial_context_builder
            if initial_context_builder is not None
            else build_initial_context_state
        )

    def initialize(
        self,
        document: Document,
    ) -> tuple[ProjectState, list[DocumentChapter]]:
        chapters = self.splitter.split(document)

        project_id = self.config.project_dir.name

        state = ProjectState(
            project_id=project_id,
            source_path=str(self.config.source_path),
            output_path=str(self.config.output_path),
            output_format=self.config.output_format,
            chapter_ids=[
                chapter.chapter_id
                for chapter in chapters
            ],
            completed_chapters=[],
            current_chapter_id=(
                chapters[0].chapter_id
                if chapters
                else None
            ),
            status=(
                "in_progress"
                if chapters
                else "completed"
            ),
        )

        return state, chapters

    def get_chapter_progress(
        self,
        chapter_id: str,
    ) -> dict:
        return self.progress_db.load(chapter_id)

    def start_chapter(
        self,
        chapter_id: str,
    ) -> dict:
        return self.progress_db.start_chapter(
            chapter_id
        )

    def process_chapter(
        self,
        state: ProjectState,
        chapter: DocumentChapter,
        chunks=None,
        chapter_context=None,
        initial_context_state=None,
        entity_resolutions=None,
    ):
        if self.chapter_processor is None:
            raise RuntimeError(
                "ChapterProcessor belum dikonfigurasi."
            )

        if chunks is None:
            chunks = self.chunk_builder(
                chapter.paragraphs
            )

        if chapter_context is None:
            chapter_context = self.context_builder(
                chapter.chapter_id,
                chapter.title,
                resolved_entities=(
                    entity_resolutions
                    if entity_resolutions is not None
                    else []
                ),
            )

        if initial_context_state is None:
            initial_context_state = (
                self.initial_context_builder()
            )

        self.start_chapter(
            chapter.chapter_id
        )

        result = self.chapter_processor.process_chapter(
            chapter.chapter_id,
            chunks,
            chapter_context,
            initial_context_state,
            entity_resolutions=entity_resolutions,
        )

        self.mark_chapter_completed(
            state,
            chapter.chapter_id,
        )

        return result

    def process_all_chapters(
        self,
        state: ProjectState,
        chapters: list[DocumentChapter],
        initial_context_state=None,
    ):
        if self.chapter_processor is None:
            raise RuntimeError(
                "ChapterProcessor belum dikonfigurasi."
            )

        results = []

        completed = set(
            state.completed_chapters
        )

        context_state = (
            initial_context_state
            if initial_context_state is not None
            else self.initial_context_builder()
        )

        for chapter in chapters:
            if chapter.chapter_id in completed:
                continue

            result = self.process_chapter(
                state,
                chapter,
                initial_context_state=context_state,
            )

            results.append(result)

            if isinstance(result, list):
                result_context = (
                    getattr(result[-1], "context_state", None)
                    if result
                    else None
                )
            else:
                result_context = getattr(
                    result,
                    "context_state",
                    None,
                )

            if result_context is not None:
                context_state = result_context

        return results

    def mark_chapter_completed(
        self,
        state: ProjectState,
        chapter_id: str,
    ) -> ProjectState:
        if (
            chapter_id
            not in state.completed_chapters
        ):
            state.completed_chapters.append(
                chapter_id
            )

        remaining = [
            chapter
            for chapter in state.chapter_ids
            if chapter
            not in state.completed_chapters
        ]

        state.current_chapter_id = (
            remaining[0]
            if remaining
            else None
        )

        state.status = (
            "completed"
            if not remaining
            else "in_progress"
        )

        return state
