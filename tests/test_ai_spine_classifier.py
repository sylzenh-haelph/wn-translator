from models.document import Paragraph, TextRun
from translation.ai_spine_classifier import (
    classify_spine_document_with_ai,
)


class FakeClient:
    def __init__(self, response):
        self.response = response

    def generate(self, prompt):
        return self.response


def make_paragraph(
    paragraph_id,
    text,
    *,
    heading_level=None,
):
    style = {}

    if heading_level is not None:
        style["heading_level"] = heading_level

    return Paragraph(
        id=paragraph_id,
        runs=[TextRun(text=text)],
        style=style,
    )


def test_ai_classifies_chapter():
    client = FakeClient(
        """
        {
          "classification": "chapter",
          "confidence": 0.92,
          "reason": "Contains a chapter heading and story content."
        }
        """
    )

    paragraphs = [
        make_paragraph(
            "p001",
            "Chapter 1",
            heading_level=1,
        ),
        make_paragraph(
            "p002",
            "The story begins here.",
        ),
    ]

    result = classify_spine_document_with_ai(
        client=client,
        paragraphs=paragraphs,
        document_id="id11",
    )

    assert result.classification == "chapter"
    assert result.confidence == 0.92
    assert result.reason


def test_ai_classifies_front_matter():
    client = FakeClient(
        """
        {
          "classification": "front_matter",
          "confidence": 0.97,
          "reason": "Short title-page style content."
        }
        """
    )

    paragraphs = [
        make_paragraph(
            "p001",
            "The Silver Gate",
        ),
        make_paragraph(
            "p002",
            "A Novel",
        ),
    ]

    result = classify_spine_document_with_ai(
        client=client,
        paragraphs=paragraphs,
        document_id="id12",
    )

    assert result.classification == "front_matter"
    assert result.confidence == 0.97
    assert result.reason


def test_ai_classifies_ambiguous():
    client = FakeClient(
        """
        {
          "classification": "ambiguous",
          "confidence": 0.50,
          "reason": "Insufficient structural evidence."
        }
        """
    )

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

    result = classify_spine_document_with_ai(
        client=client,
        paragraphs=paragraphs,
        document_id="id13",
    )

    assert result.classification == "ambiguous"
    assert result.confidence == 0.50
    assert result.reason


def test_empty_spine_document_is_ambiguous_without_ai():
    class FailingClient:
        def generate(self, prompt):
            raise AssertionError(
                "AI should not be called for an empty spine document."
            )

    result = classify_spine_document_with_ai(
        client=FailingClient(),
        paragraphs=[],
        document_id="empty",
    )

    assert result.classification == "ambiguous"
    assert result.confidence == 0.0
