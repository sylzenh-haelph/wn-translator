import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Document, Paragraph, TextRun
from reconstruction.docx_reconstructor import reconstruct_docx
from parsers.docx_parser import parse_docx


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "test_translated_chapter_docx_pipeline.docx"


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
    document = Document(
        title="Test Novel",
        author="Test Author",
    )

    chapter_1 = [
        make_paragraph(
            "p0000",
            "Chapter 1",
            heading_level=1,
            bold=True,
        ),
        make_paragraph(
            "p0001",
            "Alice memasuki istana.",
        ),
        make_paragraph(
            "p0002",
            "Ia melihat penjaga di gerbang.",
        ),
    ]

    chapter_2 = [
        make_paragraph(
            "p0003",
            "Chapter 2",
            heading_level=1,
            bold=True,
        ),
        make_paragraph(
            "p0004",
            "Marcus mengikuti Alice.",
        ),
        make_paragraph(
            "p0005",
            "Mereka berjalan menuju aula.",
        ),
    ]

    # Simulasikan hasil translation.
    chapter_1[0].runs[0].text = "Bab 1"
    chapter_2[0].runs[0].text = "Bab 2"

    paragraphs = chapter_1 + chapter_2

    translated_document = Document(
        title=document.title,
        author=document.author,
        paragraphs=paragraphs,
    )

    reconstruct_docx(
        translated_document,
        OUTPUT,
    )

    assert OUTPUT.exists()

    # Parse kembali hasil DOCX untuk memastikan output
    # benar-benar dapat dibaca oleh parser kita.
    parsed = parse_docx(OUTPUT)

    assert len(parsed.paragraphs) == 6

    expected = [
        ("p0000", "Bab 1"),
        ("p0001", "Alice memasuki istana."),
        ("p0002", "Ia melihat penjaga di gerbang."),
        ("p0003", "Bab 2"),
        ("p0004", "Marcus mengikuti Alice."),
        ("p0005", "Mereka berjalan menuju aula."),
    ]

    actual_texts = [
        paragraph.text
        for paragraph in parsed.paragraphs
    ]

    expected_texts = [
        text
        for _, text in expected
    ]

    assert actual_texts == expected_texts

    # Heading structure.
    assert parsed.paragraphs[0].style.get("name") == "Heading 1"
    assert parsed.paragraphs[3].style.get("name") == "Heading 1"

    # Formatting.
    assert parsed.paragraphs[0].runs[0].formatting.get(
        "bold"
    ) is True

    assert parsed.paragraphs[1].runs[0].formatting.get(
        "font_name"
    ) == "Calibri"

    # Chapter order must remain immutable.
    assert parsed.paragraphs[0].text == "Bab 1"
    assert parsed.paragraphs[3].text == "Bab 2"

    OUTPUT.unlink(missing_ok=True)

    print(
        "PASS: translated chapter -> DOCX reconstruction pipeline"
    )


if __name__ == "__main__":
    main()
