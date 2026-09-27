from pathlib import Path

from storage.glossary_db import GlossaryDB


def main():
    path = Path(
        "temp/test_glossary_db.json"
    )

    if path.exists():
        path.unlink()

    db = GlossaryDB(path)

    # --------------------------------------------------
    # TEST 1 — ADD
    # --------------------------------------------------
    record = db.add(
        term="Silver Sword",
        translation="Pedang Perak",
        aliases=[
            "silver sword",
            "Silver blade",
        ],
        locked=False,
        source="user",
        notes="Named weapon.",
        context="Fantasy weapon",
    )

    print("=== ADD ===")
    print(record)

    assert record["term"] == "Silver Sword"
    assert record["translation"] == "Pedang Perak"
    assert record["locked"] is False

    # --------------------------------------------------
    # TEST 2 — GET
    # --------------------------------------------------
    record = db.get(
        "Silver Sword"
    )

    print("\n=== GET ===")
    print(record)

    assert record is not None
    assert record["translation"] == "Pedang Perak"

    # Case-insensitive lookup
    record = db.get(
        "silver sword"
    )

    assert record is not None

    # --------------------------------------------------
    # TEST 3 — ALIAS
    # --------------------------------------------------
    record = db.resolve(
        "Silver blade"
    )

    print("\n=== ALIAS RESOLVE ===")
    print(record)

    assert record is not None
    assert record["term"] == "Silver Sword"

    # --------------------------------------------------
    # TEST 4 — UPDATE
    # --------------------------------------------------
    record = db.update(
        "Silver Sword",
        translation="Pedang Perak Sakti",
        notes="Updated user translation.",
    )

    print("\n=== UPDATE ===")
    print(record)

    assert (
        record["translation"]
        == "Pedang Perak Sakti"
    )

    # --------------------------------------------------
    # TEST 5 — LOCK
    # --------------------------------------------------
    record = db.lock(
        "Silver Sword"
    )

    print("\n=== LOCK ===")
    print(record)

    assert record["locked"] is True

    # --------------------------------------------------
    # TEST 6 — LOCK + TRANSLATION
    # --------------------------------------------------
    record = db.lock(
        "Silver Sword",
        translation="Pedang Perak",
    )

    print("\n=== LOCK + TRANSLATION ===")
    print(record)

    assert record["locked"] is True
    assert record["translation"] == (
        "Pedang Perak"
    )

    # --------------------------------------------------
    # TEST 7 — ADD ALIAS
    # --------------------------------------------------
    record = db.add_alias(
        "Silver Sword",
        "Pedang Perak",
    )

    print("\n=== ADD ALIAS ===")
    print(record)

    assert "Pedang Perak" in record["aliases"]

    # --------------------------------------------------
    # TEST 8 — COUNT
    # --------------------------------------------------
    assert db.count() == 1

    print("\nCount:", db.count())

    # --------------------------------------------------
    # TEST 9 — PERSISTENCE
    # --------------------------------------------------
    db2 = GlossaryDB(path)

    record = db2.get(
        "Silver Sword"
    )

    print("\n=== RELOAD ===")
    print(record)

    assert record is not None
    assert record["translation"] == (
        "Pedang Perak"
    )
    assert record["locked"] is True
    assert "Pedang Perak" in record["aliases"]

    print("\nPASS")


if __name__ == "__main__":
    main()
