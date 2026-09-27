from pathlib import Path

from research.entity_db import EntityDB


TEST_DB = Path("temp/test_research_db.json")

if TEST_DB.exists():
    TEST_DB.unlink()


db = EntityDB(TEST_DB)

print("=== ADD RESEARCH RESULT ===")

evidence = {
    "title": "Silver Sword - Example Novel Wiki",
    "url": "https://example.com/example-novel",
    "snippet": (
        "The Silver Sword is a named weapon "
        "used by the protagonist in Example Novel."
    ),
    "source": "example.com",
    "query": '"Silver Sword" item "Example Novel"',
    "confidence": 0.95,
}

result = db.add_research(
    entity_type="item",
    canonical_name="Silver Sword",
    evidence=evidence,
)

print(result)

print("\n=== RETRIEVE ===")

retrieved = db.get("Silver Sword")

print(retrieved)

print("\n=== LOCK TEST ===")

db.update(
    "proper_noun",
    "Silver Sword",
    locked=True,
    translation="Pedang Perak",
)

db.add_research(
    entity_type="item",
    canonical_name="Silver Sword",
    evidence={
        "title": "Another Source",
        "url": "https://example.org",
        "snippet": "Another research result.",
        "source": "example.org",
    },
)

locked_result = db.get("Silver Sword")

print("Locked     :", locked_result["locked"])
print("Translation:", locked_result["translation"])
print("Researches :", len(locked_result["research"]))

print("\nPASS")
