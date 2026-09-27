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
OUTPUT = ROOT / "test_navigation_roundtrip.epub"


def main():
    source = parse_epub(FIXTURE)

    translated = Document(
        title=source.title,
        author=source.author,
        paragraphs=[],
        metadata=source.metadata,
    )

    for paragraph in source.paragraphs:
        translated.paragraphs.append(
            Paragraph(
                id=paragraph.id,
                runs=[
                    TextRun(
                        text=f"TERJEMAHAN_{paragraph.id}",
                        formatting=(
                            paragraph.runs[0].formatting
                            if paragraph.runs
                            else {}
                        ),
                    )
                ],
                style=dict(paragraph.style),
            )
        )

    reconstruct_epub(
        translated,
        OUTPUT,
        source_path=FIXTURE,
    )

    assert OUTPUT.exists()

    with ZipFile(OUTPUT, "r") as zf:
        names = set(zf.namelist())

        # Navigation resource tetap ada.
        assert "OEBPS/nav.xhtml" in names

        # NCX juga tetap ada sebagai resource.
        assert "OEBPS/toc.ncx" in names

        nav = zf.read(
            "OEBPS/nav.xhtml"
        ).decode(
            "utf-8",
            errors="replace",
        )

        opf = zf.read(
            "OEBPS/content.opf"
        ).decode(
            "utf-8",
            errors="replace",
        )

    # Navigation tidak boleh hilang.
    assert "<nav" in nav
    assert "chapter1.xhtml" in nav
    assert "chapter2.xhtml" in nav

    # EPUB 2 compatibility reference tetap ada.
    assert 'toc="ncx"' in opf

    # Manifest nav tetap ada.
    assert 'id="nav"' in opf
    assert 'properties="nav"' in opf

    # Spine tetap mempertahankan urutan.
    chapter1_pos = opf.index(
        'idref="chapter1"'
    )
    chapter2_pos = opf.index(
        'idref="chapter2"'
    )

    assert chapter1_pos < chapter2_pos

    OUTPUT.unlink()

    print(
        "PASS: EPUB navigation roundtrip"
    )


if __name__ == "__main__":
    main()
