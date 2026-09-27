import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Document, Paragraph, TextRun
from translation.chapter_translation_assembler import (
    ChapterTranslationAssembler,
)
from translation.document_assembler import DocumentAssembler


ROOT = Path(__file__).resolve().parent.parent


class FakeChapterResult:
    def __init__(self, heading, paragraphs):
        self.heading = heading
        self.paragraphs = paragraphs


def paragraph(
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
                },
            )
        ],
        style=style,
    )


def main():
    source = Document(
        title="Test Novel",
        author="Test Author",
        paragraphs=[
            paragraph(
                "p0000",
                "Chapter 1",
                heading_level=1,
                bold=True,
            ),
            paragraph(
                "p0001",
                "Alice enters the palace.",
            ),
            paragraph(
                "p0002",
                "Chapter 2",
                heading_level=1,
                bold=True,
            ),
            paragraph(
                "p0003",
                "Marcus follows Alice.",
            ),
        ],
    )

    # Simulasikan hasil translation dari masing-masing chapter.
    chapter_1 = FakeChapterResult(
        heading=paragraph(
            "p0000",
            "Bab 1",
            heading_level=1,
            bold=True,
        ),
        paragraphs=[
            paragraph(
                "p0001",
                "Alice memasuki istana.",
            )
        ],
    )

    chapter_2 = FakeChapterResult(
        heading=paragraph(
            "p0002",
            "Bab 2",
            heading_level=1,
            bold=True,
        ),
        paragraphs=[
            paragraph(
                "p0003",
                "Marcus mengikuti Alice.",
            )
        ],
    )

    assembler = DocumentAssembler()

    result = assembler.assemble(
        source,
        [
            chapter_1,
            chapter_2,
        ],
    )

    assert result.title == "Test Novel"
    assert result.author == "Test Author"

    assert len(result.paragraphs) == 4

    expected_ids = [
        "p0000",
        "p0001",
        "p0002",
        "p0003",
    ]

    expected_texts = [
        "Bab 1",
        "Alice memasuki istana.",
        "Bab 2",
        "Marcus mengikuti Alice.",
    ]

    assert [
        p.id for p in result.paragraphs
    ] == expected_ids

    assert [
        p.text for p in result.paragraphs
    ] == expected_texts

    # Heading tetap terpisah dari isi chapter.
    assert result.paragraphs[0].style.get(
        "heading_level"
    ) == 1

    assert result.paragraphs[2].style.get(
        "heading_level"
    ) == 1

    # Formatting heading tetap dipertahankan.
    assert result.paragraphs[0].runs[0].formatting.get(
        "bold"
    ) is True

    assert result.paragraphs[2].runs[0].formatting.get(
        "bold"
    ) is True

    # Metadata source tidak hilang.
    assert result.metadata == source.metadata

    print(
        "PASS: DocumentAssembler chapter-result integration"
    )


if __name__ == "__main__":
    main()
