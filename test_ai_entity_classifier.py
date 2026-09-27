from parsers.docx_parser import parse_docx
from research.entity_detector import detect_entities
from research.ai_entity_classifier import classify_with_ai
from translation.model_client import GeminiClient


document = parse_docx("input/test_entities.docx")

candidates = detect_entities(document)

paragraph_map = {
    paragraph.id: paragraph.text
    for paragraph in document.paragraphs
}

client = GeminiClient()

target = None

for candidate in candidates:
    if candidate.text == "Alice":
        target = candidate
        break

if target is None:
    raise RuntimeError("Entity Alice tidak ditemukan.")

context = paragraph_map[target.source_paragraph_id]

result = classify_with_ai(
    client,
    target,
    context,
)

print("=== AI ENTITY CLASSIFICATION ===")
print("Entity     :", result.text)
print("Type       :", result.entity_type)
print("Confidence :", result.confidence)
print("Reason     :", result.reason)
