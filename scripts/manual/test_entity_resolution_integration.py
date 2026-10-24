from pathlib import Path

from research.entity_db import EntityDB
from research.entity_resolution_service import (
    EntityResolutionService,
)
from storage.glossary_db import GlossaryDB
from storage.user_rule_db import UserRuleDB


def main():
    base = Path("temp/integration_test")

    base.mkdir(
        parents=True,
        exist_ok=True,
    )

    entity_path = base / "entities.json"
    glossary_path = base / "glossary.json"
    rules_path = base / "rules.json"

    for path in (
        entity_path,
        glossary_path,
        rules_path,
    ):
        if path.exists():
            path.unlink()

    entity_db = EntityDB(entity_path)
    glossary_db = GlossaryDB(glossary_path)
    user_rule_db = UserRuleDB(rules_path)

    # --------------------------------------------------
    # CHARACTER DB
    # --------------------------------------------------
    entity_db.add(
        "character",
        "Alice",
        translation="Alice",
        source="user",
    )

    # --------------------------------------------------
    # GLOSSARY
    # --------------------------------------------------
    glossary_db.add(
        term="Silver Sword",
        translation="Pedang Perak",
        source="user",
    )

    # --------------------------------------------------
    # USER RULE
    # --------------------------------------------------
    user_rule_db.add(
        rule_id="rule_master",
        rule_type="translation",
        target="Master",
        value="Tuan Guru",
    )

    service = EntityResolutionService(
        entity_db=entity_db,
        glossary_db=glossary_db,
        user_rule_db=user_rule_db,
    )

    # --------------------------------------------------
    # TEST 1 — GLOSSARY
    # --------------------------------------------------
    result = service.resolve(
        "Silver Sword"
    )

    print("=== GLOSSARY ===")
    print(result)

    assert result.translation == (
        "Pedang Perak"
    )
    assert result.source == "glossary"
    assert result.priority == 3

    # --------------------------------------------------
    # TEST 2 — USER RULE > GLOSSARY
    # --------------------------------------------------
    glossary_db.add(
        term="Master",
        translation="Master",
        source="user",
    )

    result = service.resolve(
        "Master"
    )

    print("\n=== USER RULE > GLOSSARY ===")
    print(result)

    assert result.translation == (
        "Tuan Guru"
    )
    assert result.source == "user_rule"
    assert result.priority == 1

    # --------------------------------------------------
    # TEST 3 — CHARACTER DB > GLOSSARY
    # --------------------------------------------------
    glossary_db.add(
        term="Alice",
        translation="Alisa",
        source="user",
    )

    result = service.resolve(
        "Alice"
    )

    print("\n=== CHARACTER DB > GLOSSARY ===")
    print(result)

    assert result.translation == "Alice"
    assert result.source == "character_db"
    assert result.priority == 2

    # --------------------------------------------------
    # TEST 4 — USER LOCK > EVERYTHING
    # --------------------------------------------------
    entity_db.update(
        "character",
        "Alice",
        translation="Alice",
        locked=True,
    )

    user_rule_db.add(
        rule_id="rule_alice",
        rule_type="translation",
        target="Alice",
        value="Alisa",
    )

    result = service.resolve(
        "Alice"
    )

    print("\n=== USER LOCK > EVERYTHING ===")
    print(result)

    assert result.translation == "Alice"
    assert result.source == "user_lock"
    assert result.priority == 0
    assert result.locked is True

    # --------------------------------------------------
    # TEST 5 — AI CONTEXT FALLBACK
    # --------------------------------------------------
    result = service.resolve(
        "Unknown Term",
        ai_context={
            "Unknown Term": "Istilah Tidak Dikenal"
        },
    )

    print("\n=== AI CONTEXT ===")
    print(result)

    assert result.translation == (
        "Istilah Tidak Dikenal"
    )
    assert result.source == "ai_context"
    assert result.priority == 5

    # --------------------------------------------------
    # TEST 6 — NOTHING
    # --------------------------------------------------
    result = service.resolve(
        "Completely Unknown"
    )

    print("\n=== NOTHING ===")
    print(result)

    assert result.translation is None
    assert result.source == "none"
    assert result.priority == -1

    print("\nPASS")


if __name__ == "__main__":
    main()
