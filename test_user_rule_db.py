from pathlib import Path

from storage.user_rule_db import UserRuleDB


def main():
    path = Path(
        "temp/test_user_rule_db.json"
    )

    if path.exists():
        path.unlink()

    db = UserRuleDB(path)

    # --------------------------------------------------
    # TEST 1 — ADD
    # --------------------------------------------------
    record = db.add(
        rule_id="rule_001",
        rule_type="translation",
        target="Master",
        value="Guru",
        locked=False,
        notes="Gunakan untuk gelar karakter.",
        context="Character title",
    )

    print("=== ADD ===")
    print(record)

    assert record["rule_id"] == "rule_001"
    assert record["rule_type"] == "translation"
    assert record["target"] == "Master"
    assert record["value"] == "Guru"
    assert record["locked"] is False

    # --------------------------------------------------
    # TEST 2 — GET
    # --------------------------------------------------
    record = db.get("rule_001")

    print("\n=== GET ===")
    print(record)

    assert record is not None
    assert record["value"] == "Guru"

    # --------------------------------------------------
    # TEST 3 — FIND BY TARGET
    # --------------------------------------------------
    results = db.find_by_target("master")

    print("\n=== FIND BY TARGET ===")
    print(results)

    assert len(results) == 1
    assert results[0]["rule_id"] == "rule_001"

    # --------------------------------------------------
    # TEST 4 — ADD SECOND RULE
    # --------------------------------------------------
    record = db.add(
        rule_id="rule_002",
        rule_type="preserve",
        target="mana",
        value="mana",
        locked=True,
        notes="Jangan diterjemahkan.",
    )

    print("\n=== SECOND RULE ===")
    print(record)

    assert record["locked"] is True

    # --------------------------------------------------
    # TEST 5 — UPDATE
    # --------------------------------------------------
    record = db.update(
        "rule_001",
        value="Tuan Guru",
        notes="Revisi istilah gelar.",
    )

    print("\n=== UPDATE ===")
    print(record)

    assert record["value"] == "Tuan Guru"

    # --------------------------------------------------
    # TEST 6 — LOCK
    # --------------------------------------------------
    record = db.lock("rule_001")

    print("\n=== LOCK ===")
    print(record)

    assert record["locked"] is True

    # --------------------------------------------------
    # TEST 7 — UNLOCK
    # --------------------------------------------------
    record = db.unlock("rule_001")

    print("\n=== UNLOCK ===")
    print(record)

    assert record["locked"] is False

    # --------------------------------------------------
    # TEST 8 — COUNT
    # --------------------------------------------------
    print("\nCount:", db.count())

    assert db.count() == 2

    # --------------------------------------------------
    # TEST 9 — PERSISTENCE
    # --------------------------------------------------
    db2 = UserRuleDB(path)

    record = db2.get("rule_001")

    print("\n=== RELOAD ===")
    print(record)

    assert record is not None
    assert record["value"] == "Tuan Guru"

    record = db2.get("rule_002")

    assert record is not None
    assert record["value"] == "mana"
    assert record["locked"] is True

    print("\nPASS")


if __name__ == "__main__":
    main()
