from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapterSplitter


def test_untitled_spine_takes_title_from_its_text_not_novel_title():
    paragraphs = [Paragraph(id=f"p{i}", runs=[TextRun(f"Kalimat {i} diary.")]) for i in range(10)]
    document = Document(
        title="Novel Judul",
        paragraphs=paragraphs,
        metadata={"epub": {
            "spine": ["s1"],
            "paragraph_spine_map": {f"p{i}": "s1" for i in range(10)},
            "navigation_items": {},
        }},
    )
    chapters = DocumentChapterSplitter().split(document)
    assert len(chapters) == 1
    assert chapters[0].title == "Kalimat 0 diary."
