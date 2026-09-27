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

seen = set()

print("=== AI ENTITY CLASSIFICATION ===")

for candidate in candidates:
    if candidate.text.lower() in seen:
        continue

    seen.add(candidate.text.lower())

    context = paragraph_map[candidate.source_paragraph_id]

    result = classify_with_ai(
        client,
        candidate,
        context,
    )

    print(
        f"{result.text!r}"
        f" | type={result.entity_type}"
        f" | confidence={result.confidence:.2f}"
        f" | {result.reason}"
    )
