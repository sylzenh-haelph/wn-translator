from research.research_translation import (
    ResearchTranslationInterpreter,
)


class MockClient:
    def __init__(self, response):
        self.response = response
        self.last_prompt = None

    def generate_json(self, prompt):
        self.last_prompt = prompt
        return self.response


def main():
    evidence = [
        {
            "title": "Example Novel Wiki",
            "source": "example.com",
            "url": "https://example.com/silver-sword",
            "snippet": (
                "The Silver Sword is a named weapon "
                "used by the protagonist."
            ),
        }
    ]

    # --------------------------------------------------
    # TEST 1 — TRANSLATABLE ITEM
    # --------------------------------------------------
    client = MockClient(
        {
            "canonical_name": "Silver Sword",
            "translation_candidate": "Pedang Perak",
            "confidence": 0.91,
            "reason": (
                "The entity is a named weapon and "
                "the Indonesian translation is natural."
            ),
            "preserve_original": False,
        }
    )

    interpreter = ResearchTranslationInterpreter(
        client
    )

    result = interpreter.interpret(
        entity_text="Silver Sword",
        entity_type="item",
        evidence=evidence,
        project_title="Example Novel",
    )

    print("=== TRANSLATABLE ITEM ===")
    print(result)

    assert result.canonical_name == (
        "Silver Sword"
    )

    assert result.translation_candidate == (
        "Pedang Perak"
    )

    assert result.confidence == 0.91

    assert result.preserve_original is False

    # --------------------------------------------------
    # TEST 2 — CHARACTER SHOULD BE PRESERVED
    # --------------------------------------------------
    client = MockClient(
        {
            "canonical_name": "Alice",
            "translation_candidate": None,
            "confidence": 0.99,
            "reason": (
                "Alice is a character name and "
                "should be preserved."
            ),
            "preserve_original": True,
        }
    )

    interpreter = ResearchTranslationInterpreter(
        client
    )

    result = interpreter.interpret(
        entity_text="Alice",
        entity_type="character",
        evidence=[
            {
                "title": "Example Novel Wiki",
                "source": "example.com",
                "url": "",
                "snippet": (
                    "Alice is one of the main characters."
                ),
            }
        ],
    )

    print("\n=== CHARACTER ===")
    print(result)

    assert result.translation_candidate is None
    assert result.preserve_original is True
    assert result.confidence == 0.99

    # --------------------------------------------------
    # TEST 3 — INVALID CONFIDENCE GETS NORMALIZED
    # --------------------------------------------------
    client = MockClient(
        {
            "canonical_name": "Mystery Term",
            "translation_candidate": "Istilah Misteri",
            "confidence": 5,
            "reason": "Test normalization.",
            "preserve_original": False,
        }
    )

    interpreter = ResearchTranslationInterpreter(
        client
    )

    result = interpreter.interpret(
        entity_text="Mystery Term",
        entity_type="proper_noun",
        evidence=evidence,
    )

    print("\n=== CONFIDENCE NORMALIZATION ===")
    print(result)

    assert result.confidence == 1.0

    # --------------------------------------------------
    # TEST 4 — EMPTY TRANSLATION
    # --------------------------------------------------
    client = MockClient(
        {
            "canonical_name": "Unknown Entity",
            "translation_candidate": "",
            "confidence": 0.4,
            "reason": "Insufficient evidence.",
            "preserve_original": True,
        }
    )

    interpreter = ResearchTranslationInterpreter(
        client
    )

    result = interpreter.interpret(
        entity_text="Unknown Entity",
        entity_type="proper_noun",
        evidence=evidence,
    )

    print("\n=== EMPTY TRANSLATION ===")
    print(result)

    assert result.translation_candidate is None
    assert result.preserve_original is True

    print("\nPASS")


if __name__ == "__main__":
    main()
