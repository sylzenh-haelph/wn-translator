from parsers.docx_parser import parse_docx
from research.entity_detector import detect_entities
from research.entity_classifier import classify_candidate


document = parse_docx("input/test_entities.docx")

candidates = detect_entities(document)

paragraph_map = {
    paragraph.id: paragraph.text
    for paragraph in document.paragraphs
}

seen = set()

for candidate in candidates:
    if candidate.text.lower() in seen:
        continue

    seen.add(candidate.text.lower())

    paragraph_text = paragraph_map[candidate.source_paragraph_id]

    result = classify_candidate(
        candidate,
        paragraph_text,
    )

    print(
        f"{result.text!r}"
        f" | {result.entity_type}"
        f" | confidence={result.confidence:.2f}"
        f" | {result.reason}"
    )
