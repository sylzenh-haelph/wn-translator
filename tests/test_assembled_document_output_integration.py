import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Document, Paragraph, TextRun
from reconstruction.docx_reconstructor import reconstruct_docx
from reconstruction.epub_reconstructor import reconstruct_epub
from parsers.docx_parser import parse_docx
from parsers.epub_parser import parse_epub
from translation.document_assembler import DocumentAssembler


ROOT = Path(__file__).resolve().parent.parent
SOURCE_EPUB = ROOT / "test_navigation_fixture.epub"
OUTPUT_EPUB = ROOT / "test_assembled_output.epub"
OUTPUT_DOCX = ROOT / "test_assembled_output.docx"


class FakeChapterResult:
    def __init__(self, heading, paragraphs):
        self.heading = heading
        self.paragraphs = paragraphs


def make_paragraph(
    paragraph_id,
    text,
    heading_level=None,
    bold=False,
):
    style = {}

    if heading_level is not None:
        style["heading_level"] = heading_level
        style["name"] = f"Heading {heading_level}"

    return Paragraph(
        id=paragraph_id,
        runs=[
            TextRun(
                text=text,
                formatting={
                    "bold": bold,
                    "italic": False,
                    "underline": False,
                    "font_name": "Calibri",
                    "font_size": 12,
                },
            )
        ],
        style=style,
    )


def main():
    assert SOURCE_EPUB.exists()

    source = parse_epub(SOURCE_EPUB)

    chapter_1 = FakeChapterResult(
        heading=make_paragraph(
            "p0000",
            "Bab 1",
            heading_level=1,
            bold=True,
        ),
        paragraphs=[
            make_paragraph(
                "p0001",
                "Alice memasuki istana.",
            )
        ],
    )

    chapter_2 = FakeChapterResult(
        heading=make_paragraph(
            "p0002",
            "Bab 2",
            heading_level=1,
            bold=True,
        ),
        paragraphs=[
            make_paragraph(
                "p0003",
                "Marcus mengikuti Alice.",
            )
        ],
    )

    assembler = DocumentAssembler()

    assembled = assembler.assemble(
        source,
        [
            chapter_1,
            chapter_2,
        ],
    )

    # -------------------------
    # EPUB OUTPUT
    # -------------------------

    reconstruct_epub(
        assembled,
        OUTPUT_EPUB,
        source_path=SOURCE_EPUB,
    )

    assert OUTPUT_EPUB.exists()

    with ZipFile(OUTPUT_EPUB, "r") as archive:
        names = archive.namelist()

        assert "OEBPS/chapter1.xhtml" in names
        assert "OEBPS/chapter2.xhtml" in names
        assert "OEBPS/nav.xhtml" in names
        assert "OEBPS/toc.ncx" in names

        chapter1 = archive.read(
            "OEBPS/chapter1.xhtml"
        ).decode("utf-8")

        chapter2 = archive.read(
            "OEBPS/chapter2.xhtml"
        ).decode("utf-8")

        nav = archive.read(
            "OEBPS/nav.xhtml"
        ).decode("utf-8")

        ncx = archive.read(
            "OEBPS/toc.ncx"
        ).decode("utf-8")

    assert "Bab 1" in chapter1
    assert "Alice memasuki istana." in chapter1

    assert "Bab 2" in chapter2
    assert "Marcus mengikuti Alice." in chapter2

    assert "Bab 1" in nav
    assert "Bab 2" in nav

    assert "Bab 1" in ncx
    assert "Bab 2" in ncx

    # Parse ulang EPUB.
    parsed_epub = parse_epub(OUTPUT_EPUB)

    assert [
        p.text for p in parsed_epub.paragraphs
    ] == [
        "Bab 1",
        "Alice memasuki istana.",
        "Bab 2",
        "Marcus mengikuti Alice.",
    ]

    # -------------------------
    # DOCX OUTPUT
    # -------------------------

    reconstruct_docx(
        assembled,
        OUTPUT_DOCX,
    )

    assert OUTPUT_DOCX.exists()

    parsed_docx = parse_docx(OUTPUT_DOCX)

    assert [
        p.text for p in parsed_docx.paragraphs
    ] == [
        "Bab 1",
        "Alice memasuki istana.",
        "Bab 2",
        "Marcus mengikuti Alice.",
    ]

    assert parsed_docx.paragraphs[0].style.get(
        "name"
    ) == "Heading 1"

    assert parsed_docx.paragraphs[2].style.get(
        "name"
    ) == "Heading 1"

    assert parsed_docx.paragraphs[0].runs[0].formatting.get(
        "bold"
    ) is True

    # -------------------------
    # CLEANUP
    # -------------------------

    OUTPUT_EPUB.unlink(missing_ok=True)
    OUTPUT_DOCX.unlink(missing_ok=True)

    print(
        "PASS: assembled document -> EPUB + DOCX integration"
    )


if __name__ == "__main__":
    main()
