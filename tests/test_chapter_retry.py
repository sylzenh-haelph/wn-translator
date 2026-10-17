from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

import main
from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapter


class OneChapterSplitter:
    def split(self, document):
        return [
            DocumentChapter(
                chapter_id="chapter_001",
                title="Chapter 1: First",
                paragraphs=[
                    Paragraph(id="p1", runs=[TextRun("SOURCE ONE")])
                ],
            )
        ]


class FakeTitleTranslator:
    def __init__(self, client):
        self.client = client

    def translate(self, title, entity_resolutions=None):
        return title


class FailingProcessor:
    translation_engine = SimpleNamespace(client=object())
    progress_db = SimpleNamespace(
        load=lambda chapter_id: {"status": "not_started"}
    )

    def process_chapter(self, **kwargs):
        raise RuntimeError("429 quota")


def test_failed_chapter_is_recorded_for_retry(monkeypatch):
    monkeypatch.setattr(main, "DocumentChapterSplitter", lambda: OneChapterSplitter())
    monkeypatch.setattr(main, "ChapterTitleTranslator", FakeTitleTranslator)

    _, stats = main.process_chapters(
        document=Document(title="Test", author="Test"),
        processor=FailingProcessor(),
        config=SimpleNamespace(max_chunk_tokens=1000),
    )

    assert stats.failed_chapters == ["chapter_001"]
