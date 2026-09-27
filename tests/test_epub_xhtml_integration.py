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


FIXTURE = ROOT / "test_structure_fixture.epub"
OUTPUT = ROOT / "test_xhtml_integration_output.epub"


def main():
    document = parse_epub(FIXTURE)

    translated = Document(
        title=document.title,
        author=document.author,
        paragraphs=[],
        metadata=document.metadata,
    )

    for paragraph in document.paragraphs:
        translated.paragraphs.append(
            Paragraph(
                id=paragraph.id,
                runs=[
                    TextRun(
                        text=(
                            f"TERJEMAHAN_{paragraph.id}"
                        ),
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
        chapter1 = zf.read(
            "OEBPS/chapter1.xhtml"
        ).decode(
            "utf-8",
            errors="replace",
        )

        chapter2 = zf.read(
            "OEBPS/chapter2.xhtml"
        ).decode(
            "utf-8",
            errors="replace",
        )

    # Struktur dari XHTML asli tetap ada.
    assert "<html" in chapter1
    assert "<body" in chapter1
    assert "<html" in chapter2
    assert "<body" in chapter2

    # Teks hasil terjemahan masuk.
    assert "TERJEMAHAN" in chapter1
    assert "TERJEMAHAN" in chapter2

    # Teks sumber tidak boleh muncul utuh sebagai teks hasil.
    source_texts = {
        paragraph.id: paragraph.text
        for paragraph in document.paragraphs
    }

    chapter1_source = [
        source_texts[paragraph.id]
        for paragraph in document.paragraphs
        if document.metadata["epub"]["paragraph_spine_map"].get(
            paragraph.id
        ) == "chapter1"
    ]

    chapter2_source = [
        source_texts[paragraph.id]
        for paragraph in document.paragraphs
        if document.metadata["epub"]["paragraph_spine_map"].get(
            paragraph.id
        ) == "chapter2"
    ]

    for source_text in chapter1_source:
        if source_text.strip():
            assert source_text not in chapter1

    for source_text in chapter2_source:
        if source_text.strip():
            assert source_text not in chapter2

    OUTPUT.unlink()

    print(
        "PASS: EPUB XHTML integration"
    )


if __name__ == "__main__":
    main()
