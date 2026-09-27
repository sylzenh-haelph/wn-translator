import json

from research.ai_entity_classifier import classify_with_ai
from research.entity_detector import EntityCandidate


class FakeClient:
    def generate(self, prompt):
        print("=== PROMPT ===")
        print(prompt)
        print("=== END PROMPT ===")

        entity = None

        for line in prompt.splitlines():
            if line.startswith("Entity:"):
                entity = line.split("Entity:", 1)[1].strip()
                break

        mapping = {
            "Alice": {
                "entity_type": "character",
                "confidence": 0.98,
                "reason": "Alice is a character.",
            },
            "Royal Palace": {
                "entity_type": "place",
                "confidence": 0.95,
                "reason": "Royal Palace is a location.",
            },
            "Silver Sword": {
                "entity_type": "item",
                "confidence": 0.95,
                "reason": "Silver Sword is a weapon.",
            },
        }

        result = mapping.get(
            entity,
            {
                "entity_type": "unknown",
                "confidence": 0.0,
                "reason": "Unknown entity.",
            },
        )

        return json.dumps(result)


client = FakeClient()

tests = [
    EntityCandidate(
        text="Alice",
        entity_type="character",
        source_paragraph_id="p0000",
        reason="test",
    ),
    EntityCandidate(
        text="Royal Palace",
        entity_type="unknown",
        source_paragraph_id="p0000",
        reason="test",
    ),
    EntityCandidate(
        text="Silver Sword",
        entity_type="unknown",
        source_paragraph_id="p0000",
        reason="test",
    ),
]

context = (
    "Novel title: Integration Test Novel\n"
    "Author: Integration Author\n"
    "Source paragraph: Alice enters the Royal Palace "
    "with the Silver Sword."
)

for candidate in tests:
    print(f"\n=== TEST: {candidate.text} ===")

    result = classify_with_ai(
        client,
        candidate,
        context,
    )

    print(result)

    assert result.text == candidate.text

print("\nPASS")
