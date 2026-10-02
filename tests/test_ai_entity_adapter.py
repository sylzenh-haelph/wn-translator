from models.document import Paragraph, TextRun
from research.ai_entity_adapter import ai_entities_to_candidates
from research.ai_entity_extractor import AIEntity, AIEntityExtractionResult


def make_paragraph(paragraph_id, text):
    return Paragraph(
        id=paragraph_id,
        runs=[TextRun(text=text)],
    )


def test_entity_adapter_uses_one_batch_request_for_all_paragraphs(monkeypatch):
    calls = []

    def fake_batch_extractor(
        client,
        paragraphs,
        novel_title="",
        author="",
    ):
        calls.append(
            {
                "client": client,
                "paragraphs": paragraphs,
                "novel_title": novel_title,
                "author": author,
            }
        )

        return AIEntityExtractionResult(
            entities=[
                AIEntity(
                    text="Silver Gate",
                    entity_type="place",
                    confidence=0.99,
                    reason="Named location.",
                    source_paragraph_id="p1",
                ),
                AIEntity(
                    text="Rook",
                    entity_type="character",
                    confidence=0.98,
                    reason="Named character.",
                    source_paragraph_id="p2",
                ),
            ]
        )

    monkeypatch.setattr(
        "research.ai_entity_adapter.extract_entities_batch_with_ai",
        fake_batch_extractor,
    )

    paragraphs = [
        make_paragraph("p1", "They approached the Silver Gate."),
        make_paragraph("p2", "Rook waited beyond it."),
    ]

    candidates = ai_entities_to_candidates(
        client="fake-client",
        paragraphs=paragraphs,
        novel_title="Test Novel",
        author="Test Author",
    )

    assert len(calls) == 1
    assert calls[0]["client"] == "fake-client"
    assert calls[0]["paragraphs"] == [
        ("p1", "They approached the Silver Gate."),
        ("p2", "Rook waited beyond it."),
    ]
    assert calls[0]["novel_title"] == "Test Novel"
    assert calls[0]["author"] == "Test Author"

    assert [
        (
            candidate.text,
            candidate.entity_type,
            candidate.source_paragraph_id,
        )
        for candidate in candidates
    ] == [
        ("Silver Gate", "place", "p1"),
        ("Rook", "character", "p2"),
    ]


def test_entity_adapter_skips_empty_paragraphs_without_ai_call(monkeypatch):
    calls = []

    def fake_batch_extractor(**kwargs):
        calls.append(kwargs)
        return AIEntityExtractionResult()

    monkeypatch.setattr(
        "research.ai_entity_adapter.extract_entities_batch_with_ai",
        fake_batch_extractor,
    )

    paragraphs = [
        make_paragraph("p1", "   "),
    ]

    candidates = ai_entities_to_candidates(
        client="fake-client",
        paragraphs=paragraphs,
    )

    assert candidates == []
    assert calls == []
