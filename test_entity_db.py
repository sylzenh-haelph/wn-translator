from pathlib import Path

from research.entity_db import EntityDB


TEST_DB = Path("temp/test_entity_db.json")

if TEST_DB.exists():
    TEST_DB.unlink()


db = EntityDB(TEST_DB)

db.add(
    entity_type="character",
    canonical_name="Alice",
    aliases=["Alice-san"],
    source="research",
)

db.add(
    entity_type="character",
    canonical_name="King Arthur",
    source="research",
)

db.add(
    entity_type="proper_noun",
    canonical_name="Royal Palace",
    aliases=["the Royal Palace"],
    source="research",
)

db.add(
    entity_type="proper_noun",
    canonical_name="Silver Sword",
    source="research",
)

print("Jumlah entity:", db.count())

print("\nPencarian:")

for query in [
    "Alice",
    "Alice-san",
    "King Arthur",
    "Royal Palace",
    "the Royal Palace",
    "Silver Sword",
    "Unknown Thing",
]:
    result = db.get(query)
    print(f"{query!r} -> {result}")

print("\nSemua entity:")

for entity in db.list_all():
    print(entity)

print("\nPASS")
