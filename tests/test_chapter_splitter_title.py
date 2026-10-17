from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from models.document import Document, Paragraph, TextRun
from translation import chapter_splitter


def para(pid, text):
    return Paragraph(
        id=pid,
        runs=[TextRun(text=text)],
        style={"name": "Normal", "heading_level": None},
    )


def test_chapter_title_taken_from_chapter_paragraph(monkeypatch):
    monkeypatch.setattr(
        chapter_splitter,
        "classify_spine_document",
        lambda paragraphs: SimpleNamespace(classification="chapter"),
    )

    document = Document(
        title="Novel Besar",
        paragraphs=[
            para("p1", "Chapter 1:The Diary (Part 1)"),
            para("p2", "Alice memasuki istana."),
        ],
    )
    document.metadata = {
        "epub": {
            "spine": ["s1"],
            "paragraph_spine_map": {"p1": "s1", "p2": "s1"},
            "navigation_items": {},
        }
    }

    chapters = chapter_splitter.DocumentChapterSplitter().split(document)

    assert len(chapters) == 1
    assert chapters[0].title == "Chapter 1:The Diary (Part 1)"
    assert chapters[0].heading is None
    assert [p.id for p in chapters[0].paragraphs] == ["p1", "p2"]
