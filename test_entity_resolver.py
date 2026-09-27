from research.entity_db import EntityDB
from research.entity_detector import detect_entities
from research.entity_resolver import resolve_entities
from parsers.docx_parser import parse_docx


document = parse_docx("input/test_entities.docx")

candidates = detect_entities(document)

db = EntityDB("temp/test_entity_db.json")

results = resolve_entities(candidates, db)

print("=== ENTITY RESOLUTION ===")

for entity in results:
    print(
        f"{entity.text!r}"
        f" | type={entity.entity_type}"
        f" | status={entity.status}"
        f" | canonical={entity.canonical_name}"
        f" | translation={entity.translation}"
    )
