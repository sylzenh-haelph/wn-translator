from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_parser import parse_epub
from translation.chapter_splitter import DocumentChapterSplitter


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "input" / "test.epub"


def main():
    assert SOURCE.exists(), f"Fixture tidak ditemukan: {SOURCE}"

    document = parse_epub(SOURCE)
    chapters = DocumentChapterSplitter().split(document)

    assert len(chapters) == 1

    chapter = chapters[0]

    assert chapter.title == (
        "Chapter 1 – Written by: Nagatsuki Tappei"
    )

    assert chapter.heading is not None
    assert chapter.heading.text.strip() == (
        "Chapter 1 – Written by: Nagatsuki Tappei"
    )

    assert len(chapter.paragraphs) == 213

    paragraph_ids = [
        paragraph.id
        for paragraph in chapter.paragraphs
    ]

    assert paragraph_ids[0] == "p0004"
    assert paragraph_ids[-1] == "p0216"

    print("PASS: EPUB title page is excluded from chapter splitting")


if __name__ == "__main__":
    main()
