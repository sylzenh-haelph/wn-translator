from types import SimpleNamespace

from research.evidence_validator import EvidenceValidator


validator = EvidenceValidator()


def evidence(title, snippet, url="https://example.com/test", source="mock"):
    return SimpleNamespace(
        title=title,
        snippet=snippet,
        url=url,
        source=source,
    )


print("=== RELEVANT EVIDENCE ===")

result = validator.validate(
    entity_text="Silver Sword",
    entity_type="item",
    evidence=evidence(
        "Silver Sword - Example Novel Wiki",
        "The Silver Sword is a named weapon used by the protagonist.",
    ),
    query='"Silver Sword" item "Example Novel"',
)

print(result)
assert result.valid is True
assert result.score >= 0.5


print("\n=== IRRELEVANT EVIDENCE ===")

result = validator.validate(
    entity_text="Alice",
    entity_type="character",
    evidence=evidence(
        "Silver Sword - Fictional Item Reference",
        "The Silver Sword is a named weapon used in the novel.",
    ),
    query='"Alice" character',
)

print(result)
assert result.valid is False


print("\n=== MISSING EVIDENCE ===")

result = validator.validate(
    entity_text="Alice",
    entity_type="character",
    evidence=None,
    query='"Alice" character',
)

print(result)
assert result.valid is False


print("\n=== INVALID URL ===")

result = validator.validate(
    entity_text="Alice",
    entity_type="character",
    evidence=evidence(
        "Alice - Example Novel",
        "Alice is a character in the novel.",
        url="not-a-url",
    ),
    query='"Alice" character',
)

print(result)
assert result.valid is True


print("\nPASS")
