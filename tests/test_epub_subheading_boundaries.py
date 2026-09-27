import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_parser import parse_epub
from translation.chapter_splitter import DocumentChapterSplitter


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "test_epub_subheading_fixture.epub"


def main():
    assert SOURCE.exists()

    document = parse_epub(SOURCE)

    structure = document.metadata["epub"]

    assert structure["spine"] == [
        "chapter1",
        "chapter2",
    ]

    splitter = DocumentChapterSplitter()
    chapters = splitter.split(document)

    # Two spine documents = two chapters.
    assert len(chapters) == 2

    # ------------------------------------------------------------
    # Chapter 1
    # ------------------------------------------------------------

    chapter1 = chapters[0]

    assert chapter1.title == "Chapter 1"
    assert chapter1.heading is not None
    assert chapter1.heading.text == "Chapter 1"

    chapter1_texts = [
        paragraph.text
        for paragraph in chapter1.paragraphs
    ]

    # h2 "Scene: The Palace" must remain inside chapter 1.
    assert chapter1_texts == [
        "Alice enters the palace.",
        "Scene: The Palace",
        "The guards look at her.",
        "She continues walking.",
    ]

    # ------------------------------------------------------------
    # Chapter 2
    # ------------------------------------------------------------

    chapter2 = chapters[1]

    assert chapter2.title == "Chapter 2"
    assert chapter2.heading is not None
    assert chapter2.heading.text == "Chapter 2"

    chapter2_texts = [
        paragraph.text
        for paragraph in chapter2.paragraphs
    ]

    assert chapter2_texts == [
        "Marcus follows Alice.",
    ]

    print("PASS: EPUB subheading does not split chapter")


if __name__ == "__main__":
    main()
