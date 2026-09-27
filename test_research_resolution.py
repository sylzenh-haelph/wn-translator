from pathlib import Path

from research.entity_db import EntityDB
from research.entity_resolution_service import (
    EntityResolutionService,
)
from storage.glossary_db import GlossaryDB
from storage.user_rule_db import UserRuleDB


def make_service():
    base = Path(
        "temp/research_resolution_test"
    )

    base.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = {
        "entity": base / "entities.json",
        "glossary": base / "glossary.json",
        "rules": base / "rules.json",
    }

    for path in paths.values():
        if path.exists():
            path.unlink()

    entity_db = EntityDB(
        paths["entity"]
    )

    glossary_db = GlossaryDB(
        paths["glossary"]
    )

    user_rule_db = UserRuleDB(
        paths["rules"]
    )

    service = EntityResolutionService(
        entity_db=entity_db,
        glossary_db=glossary_db,
        user_rule_db=user_rule_db,
    )

    return (
        service,
        entity_db,
        glossary_db,
        user_rule_db,
    )


def main():
    (
        service,
        entity_db,
        glossary_db,
        user_rule_db,
    ) = make_service()

    # --------------------------------------------------
    # TEST 1 — RESEARCH ONLY
    # --------------------------------------------------
    result = service.resolve(
        "Silver Sword",
        research_translation="Pedang Perak",
    )

    print("=== RESEARCH ONLY ===")
    print(result)

    assert result.translation == (
        "Pedang Perak"
    )

    assert result.source == "research"
    assert result.priority == 4
    assert result.locked is False

    # --------------------------------------------------
    # TEST 2 — GLOSSARY > RESEARCH
    # --------------------------------------------------
    glossary_db.add(
        term="Silver Sword",
        translation="Pedang Baja",
        source="user",
    )

    result = service.resolve(
        "Silver Sword",
        research_translation="Pedang Perak",
    )

    print("\n=== GLOSSARY > RESEARCH ===")
    print(result)

    assert result.translation == (
        "Pedang Baja"
    )

    assert result.source == "glossary"
    assert result.priority == 3

    # --------------------------------------------------
    # TEST 3 — USER RULE > RESEARCH
    # --------------------------------------------------
    user_rule_db.add(
        rule_id="rule_sword",
        rule_type="translation",
        target="Silver Sword",
        value="Pedang Suci",
    )

    result = service.resolve(
        "Silver Sword",
        research_translation="Pedang Perak",
    )

    print("\n=== USER RULE > RESEARCH ===")
    print(result)

    assert result.translation == (
        "Pedang Suci"
    )

    assert result.source == "user_rule"
    assert result.priority == 1

    # --------------------------------------------------
    # TEST 4 — USER LOCK > RESEARCH
    # --------------------------------------------------
    entity_db.add(
        "item",
        "Silver Sword",
        translation="Silver Sword",
        locked=True,
        source="user",
    )

    result = service.resolve(
        "Silver Sword",
        research_translation="Pedang Perak",
    )

    print("\n=== USER LOCK > RESEARCH ===")
    print(result)

    assert result.translation == (
        "Silver Sword"
    )

    assert result.source == "user_lock"
    assert result.priority == 0
    assert result.locked is True

    # --------------------------------------------------
    # TEST 5 — RESEARCH > AI CONTEXT
    # --------------------------------------------------
    result = service.resolve(
        "Unknown Item",
        research_translation="Benda Misterius",
        ai_context={
            "Unknown Item": "Barang Tidak Dikenal"
        },
    )

    print("\n=== RESEARCH > AI CONTEXT ===")
    print(result)

    assert result.translation == (
        "Benda Misterius"
    )

    assert result.source == "research"
    assert result.priority == 4

    print("\nPASS")


if __name__ == "__main__":
    main()
