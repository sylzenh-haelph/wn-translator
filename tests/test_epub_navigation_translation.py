from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.document import Document, Paragraph, TextRun
from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import (
    reconstruct_epub,
)


FIXTURE = ROOT / "test_navigation_fixture.epub"
OUTPUT = ROOT / "test_navigation_translation.epub"


def main():
    source = parse_epub(FIXTURE)

    assert "nav" in source.metadata[
        "epub"
    ]["xhtml_sources"]

    translated = Document(
        title=source.title,
        author=source.author,
        paragraphs=[],
        metadata=source.metadata,
    )

    for paragraph in source.paragraphs:
        text = paragraph.text

        if paragraph.id == "p0000":
            text = "Bab 1"

        elif paragraph.id == "p0001":
            text = "Alice masuk."

        elif paragraph.id == "p0002":
            text = "Bab 2"

        elif paragraph.id == "p0003":
            text = "Marcus mengikuti."

        translated.paragraphs.append(
            Paragraph(
                id=paragraph.id,
                runs=[
                    TextRun(text=text)
                ],
                style=dict(paragraph.style),
            )
        )

    reconstruct_epub(
        translated,
        OUTPUT,
        source_path=FIXTURE,
    )

    with ZipFile(OUTPUT, "r") as zf:
        nav = zf.read(
            "OEBPS/nav.xhtml"
        ).decode(
            "utf-8",
            errors="replace",
        )

    assert "Bab 1" in nav
    assert "Bab 2" in nav

    assert "Chapter 1</a>" not in nav
    assert "Chapter 2</a>" not in nav

    assert 'href="chapter1.xhtml"' in nav
    assert 'href="chapter2.xhtml"' in nav

    OUTPUT.unlink()

    print(
        "PASS: EPUB navigation translation"
    )


if __name__ == "__main__":
    main()
