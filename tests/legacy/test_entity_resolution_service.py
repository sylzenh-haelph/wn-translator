from pathlib import Path

from research.entity_db import EntityDB
from research.entity_resolution_service import (
    EntityResolutionService,
)
from storage.glossary_db import GlossaryDB
from storage.user_rule_db import UserRuleDB


def fresh_path(name):
    path = Path("temp") / name
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        path.unlink()

    return path


def show(label, result):
    print(f"\n=== {label} ===")
    print("Entity      :", result.entity_text)
    print("Type        :", result.entity_type)
    print("Translation :", result.translation)
    print("Source      :", result.source)
    print("Priority    :", result.priority)
    print("Locked      :", result.locked)
    print("Reason      :", result.reason)


def build_service():
    entity_db = EntityDB(
        fresh_path("test_resolution_service_entities.json")
    )

    glossary_db = GlossaryDB(
        fresh_path("test_resolution_service_glossary.json")
    )

    user_rule_db = UserRuleDB(
        fresh_path("test_resolution_service_rules.json")
    )

    return (
        entity_db,
        glossary_db,
        user_rule_db,
        EntityResolutionService(
            entity_db=entity_db,
            glossary_db=glossary_db,
            user_rule_db=user_rule_db,
        ),
    )


def main():
    (
        entity_db,
        glossary_db,
        user_rule_db,
        service,
    ) = build_service()

    # --------------------------------------------------
    # TEST 1
    # Research exists, but research evidence alone
    # must NOT become a translation.
    # --------------------------------------------------
    entity_db.add(
        canonical_name="Silver Sword",
        entity_type="item",
        translation=None,
        aliases=[],
        locked=False,
        source="research",
        notes="Named weapon.",
    )

    entity_db.add_research(
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

    result = service.resolve("Silver Sword")

    show("RESEARCH IS EVIDENCE ONLY", result)

    assert result.translation is None
    assert result.source == "none"

    # --------------------------------------------------
    # TEST 2
    # Glossary DB provides the translation.
    # --------------------------------------------------
    glossary_db.add(
        term="Silver Sword",
        translation="Pedang Perak",
        notes="Glossary entry.",
    )

    result = service.resolve("Silver Sword")

    show("GLOSSARY", result)

    assert result.translation == "Pedang Perak"
    assert result.source == "glossary"

    # --------------------------------------------------
    # TEST 3
    # User rule overrides glossary.
    # --------------------------------------------------
    user_rule_db.add(
        rule_id="silver_sword_rule",
        rule_type="translation",
        target="Silver Sword",
        value="Pedang Perak Sakti",
        locked=False,
        notes="User rule.",
    )

    result = service.resolve("Silver Sword")

    show("USER RULE > GLOSSARY", result)

    assert result.translation == "Pedang Perak Sakti"
    assert result.source == "user_rule"

    # --------------------------------------------------
    # TEST 4
    # User lock overrides everything.
    # --------------------------------------------------
    user_rule_db.add(
        rule_id="silver_sword_lock",
        rule_type="translation",
        target="Silver Sword",
        value="Pedang Bulan",
        locked=True,
        notes="Permanent user lock.",
    )

    result = service.resolve("Silver Sword")

    show("USER LOCK > EVERYTHING", result)

    assert result.translation == "Pedang Bulan"
    assert result.source == "user_lock"
    assert result.locked is True

    # --------------------------------------------------
    # TEST 5
    # Character DB overrides glossary.
    # --------------------------------------------------
    (
        entity_db_2,
        glossary_db_2,
        user_rule_db_2,
        service_2,
    ) = build_service()

    entity_db_2.add(
        canonical_name="Alice",
        entity_type="character",
        translation="Alice",
        aliases=[],
        locked=False,
        source="research",
        notes="Character translation.",
    )

    glossary_db_2.add(
        term="Alice",
        translation="Alisa",
        notes="Glossary.",
    )

    result = service_2.resolve("Alice")

    show("CHARACTER DB > GLOSSARY", result)

    assert result.translation == "Alice"
    assert result.source == "character_db"

    # --------------------------------------------------
    # TEST 6
    # AI context is used when no stronger persistent
    # resolution source exists.
    # --------------------------------------------------
    (
        _entity_db_3,
        _glossary_db_3,
        _user_rule_db_3,
        service_3,
    ) = build_service()

    result = service_3.resolve(
        "Unknown Term",
        ai_context={
            "Unknown Term": "Istilah Tidak Dikenal",
        },
    )

    show("AI CONTEXT", result)

    assert result.translation == "Istilah Tidak Dikenal"
    assert result.source == "ai_context"

    # --------------------------------------------------
    # TEST 7
    # Completely unknown entity has no resolution.
    # --------------------------------------------------
    result = service_3.resolve(
        "Completely Unknown",
    )

    show("NOTHING", result)

    assert result.translation is None
    assert result.source == "none"

    print("\nPASS")


if __name__ == "__main__":
    main()
