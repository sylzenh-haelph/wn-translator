import sys
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapter
from translation.project_pipeline import (
    ProjectConfig,
    ProjectPipeline,
)


class FakeChapterProcessor:
    def __init__(self):
        self.calls = []

    def process_chapter(
        self,
        chapter_id,
        chunks,
        chapter_context,
        initial_context_state,
        entity_resolutions=None,
    ):
        self.calls.append(
            chapter_id
        )

        return type(
            "FakeChapterResult",
            (),
            {
                "chapter_id": chapter_id,
                "status": "completed",
                "context_state": initial_context_state,
            },
        )()


class FakeSplitter:
    def split(self, document):
        return [
            DocumentChapter(
                chapter_id="chapter_001",
                title="Bab 1",
                paragraphs=[
                    Paragraph(
                        id="p1",
                        runs=[
                            TextRun("Alice masuk.")
                        ],
                    )
                ],
            ),
            DocumentChapter(
                chapter_id="chapter_002",
                title="Bab 2",
                paragraphs=[
                    Paragraph(
                        id="p2",
                        runs=[
                            TextRun("Marcus datang.")
                        ],
                    )
                ],
            ),
        ]


ROOT = Path(
    "/storage/emulated/0/Download/projects/wn-translator"
)


def main():
    project_dir = ROOT / "test_project_processor"

    config = ProjectConfig(
        project_dir=project_dir,
        source_path=ROOT / "input.epub",
        output_path=ROOT / "output.epub",
        output_format="epub",
        progress_dir=project_dir / "progress",
    )

    processor = FakeChapterProcessor()

    pipeline = ProjectPipeline(
        config,
        splitter=FakeSplitter(),
        chapter_processor=processor,
    )

    document = Document(
        title="Test Novel",
        author="Test Author",
    )

    state, chapters = pipeline.initialize(
        document
    )

    assert state.status == "in_progress"

    results = pipeline.process_all_chapters(
        state,
        chapters,
    )

    assert len(results) == 2

    assert processor.calls == [
        "chapter_001",
        "chapter_002",
    ]

    assert state.completed_chapters == [
        "chapter_001",
        "chapter_002",
    ]

    assert state.current_chapter_id is None
    assert state.status == "completed"

    # Pastikan progress chapter benar-benar tercatat.
    progress_1 = pipeline.get_chapter_progress(
        "chapter_001"
    )

    progress_2 = pipeline.get_chapter_progress(
        "chapter_002"
    )

    assert progress_1["status"] == "in_progress"
    assert progress_2["status"] == "in_progress"

    # Pastikan chapter yang sudah selesai
    # tidak diproses ulang ketika pipeline
    # dijalankan kembali.
    second_results = pipeline.process_all_chapters(
        state,
        chapters,
    )

    assert second_results == []

    assert processor.calls == [
        "chapter_001",
        "chapter_002",
    ]

    # Cleanup test progress.
    for path in (
        project_dir / "progress"
    ).glob("*.json"):
        path.unlink(missing_ok=True)

    try:
        (project_dir / "progress").rmdir()
        project_dir.rmdir()
    except OSError:
        pass

    print(
        "PASS: ProjectPipeline -> ChapterProcessor integration"
    )


if __name__ == "__main__":
    main()
