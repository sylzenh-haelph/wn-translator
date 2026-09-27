from pathlib import Path

from research.entity_db import EntityDB
from research.entity_resolution_service import (
    EntityResolutionService,
)


def fresh_db():
    path = Path(
        "temp/test_resolution_service_db.json"
    )

    if path.exists():
        path.unlink()

    return EntityDB(path)


def show(label, result):
    print(f"\n=== {label} ===")
    print("Entity      :", result.entity_text)
    print("Type        :", result.entity_type)
    print("Translation :", result.translation)
    print("Source      :", result.source)
    print("Priority    :", result.priority)
    print("Locked      :", result.locked)
    print("Reason      :", result.reason)


def main():
    db = fresh_db()

    db.add(
        canonical_name="Silver Sword",
        entity_type="item",
        translation=None,
        aliases=[],
        locked=False,
        source="ai_classifier",
        notes="Named weapon.",
    )

    db.add_research(
        entity_type="item",
        canonical_name="Silver Sword",
        evidence={
            "title": "Example Novel Wiki",
            "url": "https://example.com/example-novel",
            "snippet": (
                "The Silver Sword is a named weapon."
            ),
            "source": "example.com",
            "query": '"Silver Sword" item',
            "confidence": 0.95,
        },
    )

    service = EntityResolutionService(db)

    # --------------------------------------------------
    # TEST 1
    # Research exists, but is NOT automatically
    # converted into a translation.
    # --------------------------------------------------
    result = service.resolve(
        "Silver Sword"
    )

    show("RESEARCH IS EVIDENCE ONLY", result)

    assert result.translation is None
    assert result.source == "none"

    # --------------------------------------------------
    # TEST 2
    # Glossary provides translation.
    # --------------------------------------------------
    result = service.resolve(
        "Silver Sword",
        glossary={
            "value": "Pedang Perak",
            "reason": "Glossary entry.",
        },
    )

    show("GLOSSARY", result)

    assert result.translation == "Pedang Perak"
    assert result.source == "glossary"

    # --------------------------------------------------
    # TEST 3
    # User Rule overrides Glossary.
    # --------------------------------------------------
    result = service.resolve(
        "Silver Sword",
        user_rule={
            "value": "Pedang Perak Sakti",
            "reason": "User rule.",
        },
        glossary={
            "value": "Pedang Perak",
            "reason": "Glossary entry.",
        },
    )

    show("USER RULE > GLOSSARY", result)

    assert result.translation == (
        "Pedang Perak Sakti"
    )
    assert result.source == "user_rule"

    # --------------------------------------------------
    # TEST 4
    # Locked DB translation becomes User Lock.
    # --------------------------------------------------
    db.update(
        "item",
        "Silver Sword",
        translation="Pedang Perak",
        locked=True,
    )

    result = service.resolve(
        "Silver Sword",
        user_rule={
            "value": "Pedang Perak Sakti",
            "reason": "User rule.",
        },
        glossary={
            "value": "Pedang",
            "reason": "Glossary entry.",
        },
        ai_context={
            "value": "Pedang Perak",
            "reason": "Chapter context.",
        },
    )

    show("LOCKED DB > EVERYTHING", result)

    assert result.translation == "Pedang Perak"
    assert result.source == "user_lock"
    assert result.locked is True

    # --------------------------------------------------
    # TEST 5
    # Character DB translation.
    # --------------------------------------------------
    db.add(
        canonical_name="Alice",
        entity_type="character",
        translation="Alice",
        aliases=[],
        locked=False,
        source="user",
        notes="Character translation.",
    )

    result = service.resolve(
        "Alice",
        glossary={
            "value": "Alisa",
            "reason": "Glossary.",
        },
    )

    show("CHARACTER DB > GLOSSARY", result)

    assert result.translation == "Alice"
    assert result.source == "character_db"

    print("\nPASS")


if __name__ == "__main__":
    main()
