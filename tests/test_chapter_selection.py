from pathlib import Path
import sys

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)
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
                paragraphs=[
                    Paragraph(
                        id="p1",
                        runs=[TextRun("SOURCE ONE")],
                    )
                ],
            ),
            DocumentChapter(
                chapter_id="chapter_002",
                title="Chapter 2: Second",
                paragraphs=[
                    Paragraph(
                        id="p2",
                        runs=[TextRun("SOURCE TWO")],
                    )
                ],
            ),
            DocumentChapter(
                chapter_id="chapter_003",
                title="Chapter 3: Third",
                paragraphs=[
                    Paragraph(
                        id="p3",
                        runs=[TextRun("SOURCE THREE")],
                    )
                ],
            ),
        ]


class FakeTitleTranslator:
    def __init__(self, client):
        self.client = client

    def translate(self, title, entity_resolutions=None):
        return f"{title} (ID)"


class FakeProcessor:
    def __init__(self):
        self.translation_engine = SimpleNamespace(
            client=object()
        )
        self.calls = []

    def process_chapter(
        self,
        chapter_id,
        chunks,
        chapter_context,
        initial_context_state,
        entity_resolutions=None,
    ):
        self.calls.append(chapter_id)

        processed = []

        for chunk in chunks:
            translated = [
                f"TRANSLATED {paragraph_text}"
                for paragraph_text in chunk.paragraph_texts
            ]

            processed.append(
                SimpleNamespace(
                    chunk_id=chunk.chunk_id,
                    translation=translated[0]
                    if len(translated) == 1
                    else "\n".join(translated),
                    paragraph_translations=translated,
                    context_state=SimpleNamespace(),
                    attempts=1,
                    qa_passed=True,
                    flagged=False,
                    issues=[],
                    cache_hit=False,
                )
            )

        return processed


def test_single_chapter_selection(monkeypatch):
    monkeypatch.setattr(
        main,
        "DocumentChapterSplitter",
        lambda: FakeSplitter(),
    )
    monkeypatch.setattr(
        main,
        "ChapterTitleTranslator",
        FakeTitleTranslator,
    )

    document = Document(
        title="Test Novel",
        author="Test Author",
    )

    processor = FakeProcessor()

    config = SimpleNamespace(
        max_chunk_tokens=1000,
    )

    translated_chapters, stats = main.process_chapters(
        document=document,
        processor=processor,
        config=config,
        chapter_selection=(2, 2),
    )

    assert processor.calls == ["chapter_002"]

    assert len(translated_chapters) == 3

    assert translated_chapters[0].chapter_id == "chapter_001"
    assert translated_chapters[0].paragraphs[0].text == "SOURCE ONE"

    assert translated_chapters[1].chapter_id == "chapter_002"
    assert (
        translated_chapters[1].paragraphs[0].text
        == "TRANSLATED SOURCE TWO"
    )

    assert translated_chapters[2].chapter_id == "chapter_003"
    assert translated_chapters[2].paragraphs[0].text == "SOURCE THREE"

    assert stats.total_chapters == 1
    assert stats.completed_chapters == 1


def test_chapter_range_selection(monkeypatch):
    monkeypatch.setattr(
        main,
        "DocumentChapterSplitter",
        lambda: FakeSplitter(),
    )
    monkeypatch.setattr(
        main,
        "ChapterTitleTranslator",
        FakeTitleTranslator,
    )

    document = Document(
        title="Test Novel",
        author="Test Author",
    )

    processor = FakeProcessor()

    config = SimpleNamespace(
        max_chunk_tokens=1000,
    )

    translated_chapters, stats = main.process_chapters(
        document=document,
        processor=processor,
        config=config,
        chapter_selection=(2, 3),
    )

    assert processor.calls == [
        "chapter_002",
        "chapter_003",
    ]

    assert len(translated_chapters) == 3

    assert translated_chapters[0].paragraphs[0].text == "SOURCE ONE"
    assert (
        translated_chapters[1].paragraphs[0].text
        == "TRANSLATED SOURCE TWO"
    )
    assert (
        translated_chapters[2].paragraphs[0].text
        == "TRANSLATED SOURCE THREE"
    )

    assert stats.total_chapters == 2
    assert stats.completed_chapters == 2


if __name__ == "__main__":
    test_single_chapter_selection(
        __import__("pytest").MonkeyPatch()
    )
