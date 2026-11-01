from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from types import SimpleNamespace

import main
from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapter


class FakeSplitter:
    def split(self, document):
        return [
            DocumentChapter(
                chapter_id="chapter_001",
                title="Chapter 1: First",
                paragraphs=[Paragraph(id="p1", runs=[TextRun("SOURCE ONE")])],
            )
        ]


class BrokenTitleTranslator:
    def __init__(self, client):
        self.client = client

    def translate(self, title, entity_resolutions=None):
        raise ValueError("Format judul hasil tidak mempertahankan label chapter.")


class FakeProcessor:
    def __init__(self):
        self.translation_engine = SimpleNamespace(client=object())
        self.progress_db = SimpleNamespace(load=lambda chapter_id: {"status": "not_started"})

    def process_chapter(self, chapter_id, chunks, chapter_context, initial_context_state, entity_resolutions=None):
        return [
            SimpleNamespace(
                chunk_id=chunk.chunk_id,
                translation="TRANSLATED",
                paragraph_translations=["TRANSLATED"] * len(chunk.paragraph_texts),
                context_state=SimpleNamespace(),
                attempts=1,
                qa_passed=True,
                flagged=False,
                issues=[],
                cache_hit=False,
            )
            for chunk in chunks
        ]


def test_title_failure_keeps_original_title(monkeypatch):
    monkeypatch.setattr(main, "DocumentChapterSplitter", lambda: FakeSplitter())
    monkeypatch.setattr(main, "ChapterTitleTranslator", BrokenTitleTranslator)

    chapters, stats = main.process_chapters(
        document=Document(title="Test Novel", author="Test Author"),
        processor=FakeProcessor(),
        config=SimpleNamespace(max_chunk_tokens=1000),
    )

    assert chapters[0].title == "Chapter 1: First"
    assert stats.completed_chapters == 1
