import sys
import shutil
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapter
from translation.chapter_processor import ChapterProcessor
from translation.project_pipeline import (
    ProjectConfig,
    ProjectPipeline,
)
from storage.progress_db import ProgressDB


ROOT = Path(
    "/storage/emulated/0/Download/projects/wn-translator"
)


class FakeTranslationEngine:
    def translate_chunk(
        self,
        chunk,
        context_state=None,
        chapter_context=None,
        entity_resolutions=None,
    ):
        translations = []

        for paragraph_text in chunk.paragraph_texts:
            translations.append(
                paragraph_text
                .replace(
                    "Alice enters.",
                    "Alice masuk.",
                )
                .replace(
                    "Marcus follows.",
                    "Marcus mengikuti.",
                )
            )

        return {
            "translation": "\n".join(translations),
            "paragraph_translations": translations,
            "context_state": context_state or {},
        }


class FakeQA:
    def check(
        self,
        source_chunk,
        translation,
        paragraph_translations=None,
        **kwargs,
    ):
        return {
            "passed": True,
            "issues": [],
        }


class FakeRetryController:
    def __init__(
        self,
        translation_engine,
        qa_checker,
    ):
        self.translation_engine = translation_engine
        self.qa_checker = qa_checker

    def translate_with_retry(
        self,
        chunk,
        context_state=None,
        chapter_context=None,
        entity_resolutions=None,
    ):
        result = self.translation_engine.translate_chunk(
            chunk,
            context_state=context_state,
            chapter_context=chapter_context,
            entity_resolutions=entity_resolutions,
        )

        qa = self.qa_checker.check(
            chunk,
            result["translation"],
            paragraph_translations=result[
                "paragraph_translations"
            ],
            chapter_context=chapter_context,
            entity_resolutions=entity_resolutions,
        )

        return SimpleNamespace(
            translation=result["translation"],
            paragraph_translations=result[
                "paragraph_translations"
            ],
            context_state=result["context_state"],
            passed=qa["passed"],
            flagged=False,
            qa_result=SimpleNamespace(
                passed=qa["passed"],
                issues=qa["issues"],
            ),
            attempts=[1],
        )


def make_paragraph(
    paragraph_id,
    text,
):
    return Paragraph(
        id=paragraph_id,
        runs=[TextRun(text)],
    )


def main():
    project_dir = (
        ROOT / "test_real_project"
    )

    # Pastikan fixture test selalu bersih.
    if project_dir.exists():
        shutil.rmtree(project_dir)

    config = ProjectConfig(
        project_dir=project_dir,
        source_path=ROOT / "input.epub",
        output_path=ROOT / "output.epub",
        output_format="epub",
        progress_dir=project_dir / "progress",
    )

    document = Document(
        title="Test Novel",
        author="Test Author",
    )

    chapters = [
        DocumentChapter(
            chapter_id="chapter_001",
            title="Chapter 1",
            paragraphs=[
                make_paragraph(
                    "p0001",
                    "Alice enters.",
                )
            ],
        ),
        DocumentChapter(
            chapter_id="chapter_002",
            title="Chapter 2",
            paragraphs=[
                make_paragraph(
                    "p0002",
                    "Marcus follows.",
                )
            ],
        ),
    ]

    class FixedSplitter:
        def split(self, document):
            return chapters

    translation_engine = FakeTranslationEngine()

    qa_checker = FakeQA()

    retry_controller = FakeRetryController(
        translation_engine,
        qa_checker,
    )

    progress_db = ProgressDB(
        config.progress_dir
    )

    chapter_processor = ChapterProcessor(
        retry_controller=retry_controller,
        progress_db=progress_db,
    )

    pipeline = ProjectPipeline(
        config,
        splitter=FixedSplitter(),
        progress_db=progress_db,
        chapter_processor=chapter_processor,
    )

    state, split_chapters = (
        pipeline.initialize(document)
    )

    assert state.chapter_ids == [
        "chapter_001",
        "chapter_002",
    ]

    results = pipeline.process_all_chapters(
        state,
        split_chapters,
    )

    assert len(results) == 2

    assert len(results[0]) == 1
    assert len(results[1]) == 1

    result_1 = results[0][0]
    result_2 = results[1][0]

    assert result_1.chunk_id == "chunk_0000"
    assert result_2.chunk_id == "chunk_0000"

    assert result_1.qa_passed is True
    assert result_2.qa_passed is True

    assert result_1.attempts == 1
    assert result_2.attempts == 1

    assert result_1.translation == (
        "Alice masuk."
    )

    assert result_2.translation == (
        "Marcus mengikuti."
    )

    assert result_1.paragraph_translations == [
        "Alice masuk."
    ]

    assert result_2.paragraph_translations == [
        "Marcus mengikuti."
    ]

    saved_1 = progress_db.get_chunk(
        "chapter_001",
        "chunk_0000",
    )

    saved_2 = progress_db.get_chunk(
        "chapter_002",
        "chunk_0000",
    )

    assert saved_1 is not None
    assert saved_2 is not None

    assert saved_1["qa_passed"] is True
    assert saved_2["qa_passed"] is True

    assert saved_1["translation"] == (
        "Alice masuk."
    )

    assert saved_2["translation"] == (
        "Marcus mengikuti."
    )

    assert saved_1[
        "paragraph_translations"
    ] == [
        "Alice masuk."
    ]

    assert saved_2[
        "paragraph_translations"
    ] == [
        "Marcus mengikuti."
    ]

    assert state.completed_chapters == [
        "chapter_001",
        "chapter_002",
    ]

    assert state.current_chapter_id is None

    assert state.status == "completed"

    print(
        "PASS: real ChapterProcessor "
        "project integration"
    )

    shutil.rmtree(project_dir)


if __name__ == "__main__":
    main()
