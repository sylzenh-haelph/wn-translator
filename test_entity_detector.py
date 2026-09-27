from parsers.docx_parser import parse_docx
from research.entity_detector import detect_entities


document = parse_docx("input/test_entities.docx")

entities = detect_entities(document)

print("Entities:", len(entities))

for entity in entities:
    print()
    print("TEXT:", entity.text)
    print("TYPE:", entity.entity_type)
    print("PARAGRAPH:", entity.source_paragraph_id)
    print("REASON:", entity.reason)
