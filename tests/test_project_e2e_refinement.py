import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapter
from translation.chapter_context import ContextState
from translation.chapter_processor import ChapterProcessor
from translation.project_pipeline import ProjectConfig, ProjectPipeline
from translation.translation_engine import TranslationEngine
from translation.refinement_engine import RefinementEngine
from qa.retry_controller import RetryController
from qa.rule_based_qa import run_qa
from storage.progress_db import ProgressDB


class FakeModelClient:
    def __init__(self):
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)

        if len(self.calls) == 1:
            return (
                '{"translation":"Translation: Alice masuk.\\n'
                'Marcus mengikuti.",'
                '"paragraph_translations":['
                '"Translation: Alice masuk.",'
                '"Marcus mengikuti."],'
                '"context_state":{"scene":"before-refinement"}}'
            )

        return (
            '{"translation":"Alice masuk.\\nMarcus mengikuti.",'
            '"paragraph_translations":['
            '"Alice masuk.","Marcus mengikuti."],'
            '"context_state":{"scene":"after-refinement"}}'
        )


def make_paragraph(paragraph_id, text):
    return Paragraph(
        id=paragraph_id,
        runs=[TextRun(text)],
    )


def test_project_e2e_translation_qa_refinement_progress(tmp_path):
    client = FakeModelClient()

    translation_engine = TranslationEngine(
        client=client,
    )

    refinement_engine = RefinementEngine(
        client=client,
    )

    retry_controller = RetryController(
        translation_engine=translation_engine,
        qa_function=run_qa,
        max_retries=1,
        refinement_engine=refinement_engine,
    )

    progress_db = ProgressDB(
        tmp_path / "progress",
    )

    chapter_processor = ChapterProcessor(
        retry_controller=retry_controller,
        progress_db=progress_db,
    )

    config = ProjectConfig(
        project_dir=tmp_path,
        source_path=tmp_path / "input.epub",
        output_path=tmp_path / "output.epub",
        output_format="epub",
        progress_dir=tmp_path / "progress",
    )

    document = Document(
        title="Test Novel",
        author="Test Author",
    )

    chapter = DocumentChapter(
        chapter_id="chapter_001",
        title="Chapter 1",
        paragraphs=[
            make_paragraph(
                "p0001",
                "Alice enters.",
            ),
            make_paragraph(
                "p0002",
                "Marcus follows.",
            ),
        ],
    )

    class FixedSplitter:
        def split(self, document):
            return [chapter]

    pipeline = ProjectPipeline(
        config,
        splitter=FixedSplitter(),
        progress_db=progress_db,
        chapter_processor=chapter_processor,
    )

    state, split_chapters = pipeline.initialize(
        document,
    )

    results = pipeline.process_all_chapters(
        state,
        split_chapters,
    )

    assert len(results) == 1
    assert len(results[0]) == 1

    result = results[0][0]

    assert result.qa_passed is True
    assert result.attempts == 2

    assert result.translation == (
        "Alice masuk.\nMarcus mengikuti."
    )

    assert result.paragraph_translations == [
        "Alice masuk.",
        "Marcus mengikuti.",
    ]

    assert len(client.calls) == 2

    assert (
        "Translation: Alice masuk."
        in client.calls[1]
    )

    assert (
        "unexpected_model_text"
        in client.calls[1]
    )

    assert (
        result.context_state.scene
        == "after-refinement"
    )

    progress = progress_db.load(
        "chapter_001",
    )

    assert len(progress["chunks"]) == 1
    saved_chunk = next(iter(progress["chunks"].values()))
    assert saved_chunk["qa_passed"] is True
    assert saved_chunk["translation"] == (
        "Alice masuk.\nMarcus mengikuti."
    )
