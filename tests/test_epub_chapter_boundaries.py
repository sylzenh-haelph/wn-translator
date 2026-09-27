import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_parser import parse_epub
from translation.chapter_splitter import DocumentChapterSplitter


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "test_structure_fixture.epub"


def main():
    assert SOURCE.exists(), f"Fixture tidak ditemukan: {SOURCE}"

    document = parse_epub(SOURCE)

    structure = document.metadata["epub"]

    assert structure["spine"] == [
        "chapter1",
        "chapter2",
    ]

    splitter = DocumentChapterSplitter()
    chapters = splitter.split(document)

    # ============================================================
    # Current expected architectural behavior:
    #
    # EPUB spine has two XHTML documents => two chapters.
    # ============================================================

    assert len(chapters) == 2

    assert chapters[0].chapter_id == "chapter_001"
    assert chapters[1].chapter_id == "chapter_002"

    assert chapters[0].title == "Chapter 1"
    assert chapters[1].title == "Chapter 2"

    # ============================================================
    # Paragraph IDs must remain in original order.
    # ============================================================

    first_ids = [
        paragraph.id
        for paragraph in chapters[0].paragraphs
    ]

    second_ids = [
        paragraph.id
        for paragraph in chapters[1].paragraphs
    ]

    assert first_ids == [
        "p0001",
    ]

    assert second_ids == [
        "p0003",
    ]

    # ============================================================
    # Heading must be preserved separately.
    # ============================================================

    assert chapters[0].heading is not None
    assert chapters[0].heading.id == "p0000"
    assert chapters[0].heading.text == "Chapter 1"

    assert chapters[1].heading is not None
    assert chapters[1].heading.id == "p0002"
    assert chapters[1].heading.text == "Chapter 2"

    print("PASS: EPUB chapter boundaries")


if __name__ == "__main__":
    main()
