from dataclasses import dataclass

import research.ai_entity_adapter as adapter


@dataclass
class FakeEntity:
    text: str
    entity_type: str
    reason: str


@dataclass
class FakeResult:
    entities: list


def fake_extract_entities_with_ai(
    client,
    text,
    novel_title="",
    author="",
):
    mapping = {
        "Alice enters the Royal Palace.": [
            FakeEntity(
                text="Alice",
                entity_type="character",
                reason="Named character.",
            ),
            FakeEntity(
                text="Royal Palace",
                entity_type="place",
                reason="Named location.",
            ),
        ],
        "Alice draws the Silver Sword.": [
            FakeEntity(
                text="Alice",
                entity_type="character",
                reason="Named character.",
            ),
            FakeEntity(
                text="Silver Sword",
                entity_type="item",
                reason="Named weapon.",
            ),
        ],
    }

    return FakeResult(
        entities=mapping.get(text, [])
    )


adapter.extract_entities_with_ai = (
    fake_extract_entities_with_ai
)


@dataclass
class Paragraph:
    id: str
    text: str


paragraphs = [
    Paragraph(
        id="p0001",
        text="Alice enters the Royal Palace.",
    ),
    Paragraph(
        id="p0002",
        text="Alice draws the Silver Sword.",
    ),
]


candidates = adapter.ai_entities_to_candidates(
    client=object(),
    paragraphs=paragraphs,
    novel_title="Integration Test Novel",
    author="Integration Author",
)


assert len(candidates) == 3

assert candidates[0].text == "Alice"
assert candidates[0].entity_type == "character"
assert candidates[0].source_paragraph_id == "p0001"

assert candidates[1].text == "Royal Palace"
assert candidates[1].entity_type == "place"
assert candidates[1].source_paragraph_id == "p0001"

assert candidates[2].text == "Silver Sword"
assert candidates[2].entity_type == "item"
assert candidates[2].source_paragraph_id == "p0002"

assert all(
    candidate.reason.startswith("ai_extraction:")
    for candidate in candidates
)

print("AI ENTITY ADAPTER: PASS")
