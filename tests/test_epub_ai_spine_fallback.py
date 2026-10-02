from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapterSplitter
from translation.epub_spine_classifier import SpineClassificationResult


def make_paragraph(
    paragraph_id,
    text,
    *,
    heading_level=None,
    bold=False,
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


def make_document():
    paragraphs = [
        make_paragraph(
            "p001",
            "The Silver Gate",
            bold=True,
        ),
        make_paragraph(
            "p002",
            "Re: Zero and Mushoku Tensei",
            bold=True,
        ),
        make_paragraph(
            "p005",
            "(Part 1)",
            bold=True,
        ),
        make_paragraph(
            "p003",
            "Chapter 1",
            heading_level=1,
        ),
        make_paragraph(
            "p004",
            "The story begins.",
        ),
    ]

    return Document(
        title="Test Novel",
        author="Test Author",
        paragraphs=paragraphs,
        metadata={
            "epub": {
                "spine": [
                    "front",
                    "chapter",
                ],
                "paragraph_spine_map": {
                    "p001": "front",
                    "p002": "front",
                    "p005": "front",
                    "p003": "chapter",
                    "p004": "chapter",
                },
            }
        },
    )


def test_deterministic_front_matter_does_not_call_ai():
    calls = []

    def ai_classifier(paragraphs, document_id, document):
        calls.append(document_id)
        return SpineClassificationResult(
            classification="chapter",
            confidence=1.0,
            reason="AI result",
        )

    chapters = DocumentChapterSplitter(
        ai_classifier=ai_classifier,
    ).split(make_document())

    assert calls == []
    assert len(chapters) == 1
    assert chapters[0].title == "Chapter 1"
    assert chapters[0].paragraphs[0].text == "The story begins."


def test_deterministic_chapter_does_not_call_ai():
    calls = []

    def ai_classifier(paragraphs, document_id, document):
        calls.append(document_id)
        return SpineClassificationResult(
            classification="ambiguous",
            confidence=0.5,
            reason="AI result",
        )

    chapters = DocumentChapterSplitter(
        ai_classifier=ai_classifier,
    ).split(make_document())

    assert calls == []
    assert len(chapters) == 1


def test_ambiguous_spine_calls_ai():
    paragraphs = [
        make_paragraph(
            "p001",
            "Something happened.",
        ),
        make_paragraph(
            "p002",
            "Nobody knew why.",
        ),
    ]

    document = Document(
        title="Test Novel",
        author="Test Author",
        paragraphs=paragraphs,
        metadata={
            "epub": {
                "spine": ["ambiguous"],
                "paragraph_spine_map": {
                    "p001": "ambiguous",
                    "p002": "ambiguous",
                },
            }
        },
    )

    calls = []

    def ai_classifier(
        source_paragraphs,
        document_id,
        source_document,
    ):
        calls.append(
            (
                document_id,
                len(source_paragraphs),
                source_document.title,
            )
        )

        return SpineClassificationResult(
            classification="chapter",
            confidence=0.9,
            reason="AI classified it as a chapter.",
        )

    chapters = DocumentChapterSplitter(
        ai_classifier=ai_classifier,
    ).split(document)

    assert calls == [
        ("ambiguous", 2, "Test Novel"),
    ]
    assert len(chapters) == 1
    assert chapters[0].title == "Test Novel"
    assert len(chapters[0].paragraphs) == 2


def test_navigation_spine_is_skipped_before_classification():
    paragraphs = [
        make_paragraph(
            "p000",
            "Contents",
            heading_level=1,
        ),
        make_paragraph(
            "p001",
            "Chapter 1",
            heading_level=1,
        ),
        make_paragraph(
            "p002",
            "The story begins.",
        ),
    ]

    document = Document(
        title="Test Novel",
        author="Test Author",
        paragraphs=paragraphs,
        metadata={
            "epub": {
                "spine": [
                    "nav",
                    "chapter",
                ],
                "paragraph_spine_map": {
                    "p000": "nav",
                    "p001": "chapter",
                    "p002": "chapter",
                },
                "navigation_items": {
                    "nav": {
                        "href": "nav.xhtml",
                        "media_type": "application/xhtml+xml",
                        "properties": "nav",
                    },
                },
            }
        },
    )

    calls = []

    def ai_classifier(
        source_paragraphs,
        document_id,
        source_document,
    ):
        calls.append(document_id)
        return SpineClassificationResult(
            classification="chapter",
            confidence=1.0,
            reason="AI result",
        )

    chapters = DocumentChapterSplitter(
        ai_classifier=ai_classifier,
    ).split(document)

    assert calls == []
    assert len(chapters) == 1
    assert chapters[0].title == "Chapter 1"
    assert chapters[0].paragraphs[0].text == "The story begins."

