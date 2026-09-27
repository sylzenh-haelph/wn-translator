import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub
from translation.chapter_splitter import DocumentChapterSplitter
from translation.chapter_reconstructor import ChapterReconstructor


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "test_navigation_fixture.epub"
OUTPUT = ROOT / "test_translated_chapter_navigation_pipeline.epub"


def main():
    assert SOURCE.exists(), f"Fixture tidak ditemukan: {SOURCE}"

    document = parse_epub(SOURCE)

    splitter = DocumentChapterSplitter()
    chapters = splitter.split(document)

    assert len(chapters) == 2

    # Simulasikan hasil translation chapter 1.
    chapters[0].heading.runs[0].text = "Bab 1"

    chapters[0].paragraphs[0].runs[0].text = (
        "Alice memasuki istana."
    )

    # Simulasikan hasil translation chapter 2.
    chapters[1].heading.runs[0].text = "Bab 2"

    chapters[1].paragraphs[0].runs[0].text = (
        "Marcus mengikuti Alice."
    )

    # Rebuild document dari hasil chapter.
    assembled_paragraphs = []

    for chapter in chapters:
        if chapter.heading is not None:
            assembled_paragraphs.append(chapter.heading)

        assembled_paragraphs.extend(chapter.paragraphs)

    document.paragraphs = assembled_paragraphs

    reconstruct_epub(
        document,
        OUTPUT,
        source_path=SOURCE,
    )

    assert OUTPUT.exists()

    with ZipFile(OUTPUT, "r") as archive:
        nav = archive.read(
            "OEBPS/nav.xhtml"
        ).decode("utf-8")

        ncx = archive.read(
            "OEBPS/toc.ncx"
        ).decode("utf-8")

        chapter1 = archive.read(
            "OEBPS/chapter1.xhtml"
        ).decode("utf-8")

        chapter2 = archive.read(
            "OEBPS/chapter2.xhtml"
        ).decode("utf-8")

    # EPUB 3 navigation.
    assert "Bab 1" in nav
    assert "Bab 2" in nav
    assert "Chapter 1" not in nav
    assert "Chapter 2" not in nav

    # EPUB 2 navigation.
    assert "Bab 1" in ncx
    assert "Bab 2" in ncx
    assert "Chapter 1" not in ncx
    assert "Chapter 2" not in ncx

    # Actual chapter content.
    assert "Bab 1" in chapter1
    assert "Alice memasuki istana." in chapter1

    assert "Bab 2" in chapter2
    assert "Marcus mengikuti Alice." in chapter2

    # Links must remain unchanged.
    assert "chapter1.xhtml" in nav
    assert "chapter2.xhtml" in nav
    assert 'src="chapter1.xhtml"' in ncx
    assert 'src="chapter2.xhtml"' in ncx

    OUTPUT.unlink(missing_ok=True)

    print(
        "PASS: translated chapter -> EPUB navigation pipeline"
    )


if __name__ == "__main__":
    main()
