from research.entity_types import EntityCandidate
from research.ai_entity_extractor import extract_entities_batch_with_ai


def ai_entities_to_candidates(
    client,
    paragraphs,
    novel_title="",
    author="",
):
    """
    Extract entities from a paragraph collection using one Gemini request
    and convert them into the existing EntityCandidate representation.

    The batch extractor preserves the exact source_paragraph_id returned
    by the model, so entity research can still trace each candidate back
    to its source paragraph.
    """
    normalized_paragraphs = []

    for paragraph in paragraphs:
        text = paragraph.text

        if not text.strip():
            continue

        normalized_paragraphs.append(
            (paragraph.id, text)
        )

    if not normalized_paragraphs:
        return []

    result = extract_entities_batch_with_ai(
        client=client,
        paragraphs=normalized_paragraphs,
        novel_title=novel_title,
        author=author,
    )

    candidates = []
    seen = set()

    for entity in result.entities:
        key = entity.text.casefold()

        if key in seen:
            continue

        seen.add(key)

        candidates.append(
            EntityCandidate(
                text=entity.text,
                entity_type=entity.entity_type,
                source_paragraph_id=entity.source_paragraph_id,
                reason=(
                    "ai_extraction: "
                    + entity.reason
                ),
            )
        )

    return candidates
