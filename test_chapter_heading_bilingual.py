from translation.chapter_reconstructor import ChapterReconstructor
from models.document import Paragraph, TextRun


def test_bilingual_heading_preserves_structure_and_formatting():
    heading = Paragraph(
        id="p0000",
        runs=[
            TextRun(
                text="Chapter 1",
                formatting={
                    "bold": True,
                    "font_size": 18,
                },
            )
        ],
        style={
            "heading_level": 1,
            "alignment": "center",
        },
    )

    source = [
        Paragraph(
            id="p0001",
            runs=[
                TextRun(
                    text="Alice enters the palace.",
                    formatting={},
                )
            ],
            style={},
        )
    ]

    result = ChapterReconstructor().reconstruct(
        chapter_id="chapter_001",
        title="Chapter 1: The Gate (Gerbang)",
        source_paragraphs=source,
        translated_paragraphs=[
            "Alice memasuki istana."
        ],
        heading=heading,
    )

    assert result.title == "Chapter 1: The Gate (Gerbang)"

    assert result.heading is not None
    assert result.heading.id == "p0000"
    assert result.heading.text == (
        "Chapter 1: The Gate (Gerbang)"
    )

    assert result.heading.style == {
        "heading_level": 1,
        "alignment": "center",
    }

    assert result.heading.runs[0].formatting == {
        "bold": True,
        "font_size": 18,
    }

    assert len(result.paragraphs) == 1
    assert result.paragraphs[0].id == "p0001"
    assert result.paragraphs[0].text == (
        "Alice memasuki istana."
    )


def test_empty_heading_runs_are_supported():
    heading = Paragraph(
        id="p0000",
        runs=[],
        style={"heading_level": 1},
    )

    result = ChapterReconstructor().reconstruct(
        chapter_id="chapter_001",
        title="Chapter 1: The Gate (Gerbang)",
        source_paragraphs=[],
        translated_paragraphs=[],
        heading=heading,
    )

    assert result.heading is not None
    assert result.heading.text == (
        "Chapter 1: The Gate (Gerbang)"
    )
    assert len(result.heading.runs) == 1


if __name__ == "__main__":
    test_bilingual_heading_preserves_structure_and_formatting()
    test_empty_heading_runs_are_supported()

    print("CHAPTER HEADING BILINGUAL TEST: PASS")
