import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "test_epub_subheading_fixture.epub"
OUTPUT = ROOT / "test_epub_subheading_translation_output.epub"


def main():
    document = parse_epub(SOURCE)

    translated_paragraphs = []

    for paragraph in document.paragraphs:
        translations = {
            "p0000": "Bab 1",
            "p0001": "Alice memasuki istana.",
            "p0002": "Adegan: Istana",
            "p0003": "Para penjaga melihatnya.",
            "p0004": "Dia terus berjalan.",
            "p0005": "Bab 2",
            "p0006": "Marcus mengikuti Alice.",
        }

        translated_paragraphs.append(
            translations[paragraph.id]
        )

    translated_document = document

    for paragraph, translation in zip(
        translated_document.paragraphs,
        translated_paragraphs,
    ):
        if paragraph.runs:
            paragraph.runs[0].text = translation

    reconstruct_epub(
        translated_document,
        OUTPUT,
        source_path=SOURCE,
    )

    assert OUTPUT.exists()

    with ZipFile(OUTPUT, "r") as archive:
        chapter1 = archive.read(
            "OEBPS/chapter1.xhtml"
        ).decode("utf-8")

        chapter2 = archive.read(
            "OEBPS/chapter2.xhtml"
        ).decode("utf-8")

    # Chapter heading translated.
    assert "Bab 1" in chapter1

    # Subheading translated and still remains an h2.
    assert "<h2>Adegan: Istana</h2>" in chapter1

    # Other paragraphs translated.
    assert "Alice memasuki istana." in chapter1
    assert "Para penjaga melihatnya." in chapter1
    assert "Dia terus berjalan." in chapter1

    # Chapter 2 remains separate.
    assert "Bab 2" in chapter2
    assert "Marcus mengikuti Alice." in chapter2

    # Subheading must NOT become a separate XHTML file.
    assert "subheading" not in archive.namelist()

    OUTPUT.unlink(missing_ok=True)

    print("PASS: EPUB subheading translation")


if __name__ == "__main__":
    main()
