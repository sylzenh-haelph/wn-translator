from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Paragraph, TextRun
from translation.epub_spine_classifier import (
    classify_spine_document,
    is_likely_front_matter,
)


def make_paragraph(
    paragraph_id,
    text,
    *,
    bold=False,
    heading_level=None,
):
    style = {}

    if heading_level is not None:
        style["heading_level"] = heading_level

    return Paragraph(
        id=paragraph_id,
        runs=[
            TextRun(
                text=text,
                formatting={"bold": bold},
            )
        ],
        style=style,
    )


def test_title_page_is_front_matter():
    paragraphs = [
        make_paragraph("p1", "The Silver Gate", bold=True),
        make_paragraph("p2", "A Novel", bold=True),
        make_paragraph("p3", "Written by Example Author", bold=True),
    ]

    assert is_likely_front_matter(paragraphs) is True


def test_heading_document_is_not_front_matter():
    paragraphs = [
        make_paragraph(
            "p1",
            "Chapter 1",
            heading_level=1,
        ),
        make_paragraph(
            "p2",
            "The gate stood before him.",
        ),
    ]

    assert is_likely_front_matter(paragraphs) is False


def test_chapter_marker_is_not_front_matter():
    paragraphs = [
        make_paragraph("p1", "Chapter 1", bold=True),
        make_paragraph(
            "p2",
            "The beginning of the story.",
            bold=True,
        ),
    ]

    assert is_likely_front_matter(paragraphs) is False


def test_mixed_formatting_is_not_front_matter():
    paragraphs = [
        make_paragraph("p1", "The Silver Gate", bold=True),
        make_paragraph("p2", "This is ordinary text."),
    ]

    assert is_likely_front_matter(paragraphs) is False


def test_long_document_is_not_front_matter():
    paragraphs = [
        make_paragraph(
            f"p{index}",
            f"Paragraph {index}",
            bold=True,
        )
        for index in range(9)
    ]

    assert is_likely_front_matter(paragraphs) is False


def test_empty_document_is_not_front_matter():
    assert is_likely_front_matter([]) is False



def test_classify_front_matter():
    paragraphs = [
        make_paragraph("p1", "The Silver Gate", bold=True),
        make_paragraph("p2", "A Novel", bold=True),
        make_paragraph("p3", "Written by Example Author", bold=True),
    ]

    result = classify_spine_document(paragraphs)

    assert result.classification == "front_matter"
    assert result.confidence >= 0.9


def test_classify_chapter():
    paragraphs = [
        make_paragraph(
            "p1",
            "Chapter 1",
            heading_level=1,
        ),
        make_paragraph("p2", "The gate stood before him."),
    ]

    result = classify_spine_document(paragraphs)

    assert result.classification == "chapter"
    assert result.confidence >= 0.9


def test_classify_ambiguous():
    paragraphs = [
        make_paragraph("p1", "A short piece of text."),
        make_paragraph("p2", "Another short piece."),
    ]

    result = classify_spine_document(paragraphs)

    assert result.classification == "ambiguous"
    assert 0.0 <= result.confidence <= 1.0


def main():
    test_title_page_is_front_matter()
    test_heading_document_is_not_front_matter()
    test_chapter_marker_is_not_front_matter()
    test_mixed_formatting_is_not_front_matter()
    test_long_document_is_not_front_matter()
    test_empty_document_is_not_front_matter()

    print("PASS: EPUB spine front-matter classifier")


if __name__ == "__main__":
    main()
