from __future__ import annotations

from dataclasses import dataclass, field

from translation.model_client import extract_json


VALID_TYPES = {
    "character",
    "place",
    "organization",
    "item",
    "skill",
    "race",
    "title",
    "proper_noun",
}


@dataclass
class AIEntity:
    text: str
    entity_type: str
    confidence: float
    reason: str = ""
    source_paragraph_id: str = ""


@dataclass
class AIEntityExtractionResult:
    entities: list[AIEntity] = field(default_factory=list)


def _normalize_entity(item):
    if not isinstance(item, dict):
        return None

    text = item.get("text")
    if not isinstance(text, str):
        return None

    text = text.strip()
    if not text:
        return None

    entity_type = item.get("entity_type", "proper_noun")
    if entity_type not in VALID_TYPES:
        entity_type = "proper_noun"

    try:
        confidence = float(item.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))

    reason = item.get("reason", "")
    if not isinstance(reason, str):
        reason = str(reason)

    paragraph_id = item.get("source_paragraph_id", "")
    if not isinstance(paragraph_id, str):
        paragraph_id = str(paragraph_id)

    paragraph_id = paragraph_id.strip()

    return AIEntity(
        text=text,
        entity_type=entity_type,
        confidence=confidence,
        reason=reason.strip(),
        source_paragraph_id=paragraph_id,
    )


def _deduplicate(entities):
    result = []
    seen = set()

    for entity in entities:
        key = (
            entity.text.casefold(),
            entity.source_paragraph_id,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(entity)

    return result


def _build_prompt(paragraphs, novel_title="", author=""):
    source_blocks = []

    for paragraph_id, text in paragraphs:
        source_blocks.append(
            f'PARAGRAPH_ID: {paragraph_id}\n'
            f'TEXT:\n{text}'
        )

    source_text = "\n\n".join(source_blocks)

    return f"""
You are an entity extraction system for an English fantasy novel.

Your task is to identify ONLY specific named entities or terms
that may need persistent translation handling or research.

Entity types:
- character: named people or characters
- place: named locations, regions, cities, kingdoms, buildings, etc.
- organization: named groups, factions, orders, institutions
- item: named objects, weapons, artifacts, books, maps, etc.
- skill: named abilities, techniques, spells, powers
- race: named fictional races or species
- title: specific titles/ranks when they function as a named term
- proper_noun: other specific named terms

IMPORTANT RULES:

1. Do NOT extract ordinary common nouns.
2. Do NOT extract ordinary verbs, adjectives, pronouns, or adverbs.
3. Do NOT extract words merely because they are capitalized.
4. A word at the beginning of a sentence is NOT automatically an entity.
5. Preserve the exact entity wording from the source when possible.
6. If a multi-word expression is one named entity, return it as one entity.
7. Do not create entities by combining words from separate sentences.
8. Use surrounding context to determine whether something is actually
   a named entity.
9. Be conservative: false positives are worse than missing an ordinary word.
10. Do not extract generic terms such as "kingdom", "gate", "city",
    "map", "hall", "order", or "records" unless the text clearly uses
    the expression as a specific name.
11. Do not extract chapter headings or table-of-contents labels.
12. Do not invent entities that are not present in the source text.
13. Every entity MUST belong to one of the supplied paragraph IDs.
14. The source_paragraph_id MUST exactly match the PARAGRAPH_ID where
    the entity appears.
15. Do not combine text from different paragraphs into one entity.
16. If the same character appears under a shortened name in another
    paragraph, keep the exact form used in that paragraph.
17. Ignore ordinary dialogue words such as "No", "Yes", "Look", etc.
18. Ignore sentence-initial capitalization unless context proves it is
    a proper name.
19. Do not extract a normal title such as "Mr.", "Sir", "Captain",
    "King", etc. unless it functions as a specific named title in context.

Novel title: {novel_title}
Author: {author}

SOURCE PARAGRAPHS:

{source_text}

Return ONLY valid JSON in exactly this structure:

{{
  "entities": [
    {{
      "text": "exact source entity",
      "entity_type": "character",
      "confidence": 0.99,
      "reason": "brief contextual reason",
      "source_paragraph_id": "exact paragraph id"
    }}
  ]
}}

If there are no entities, return:

{{
  "entities": []
}}
""".strip()


def extract_entities_batch_with_ai(
    client,
    paragraphs,
    novel_title="",
    author="",
):
    """
    Extract entities from multiple paragraphs using ONE Gemini request.

    paragraphs:
        iterable of (paragraph_id, text)
    """

    normalized_paragraphs = []

    for paragraph_id, text in paragraphs:
        if not isinstance(paragraph_id, str):
            paragraph_id = str(paragraph_id)

        if not isinstance(text, str):
            continue

        if not text.strip():
            continue

        normalized_paragraphs.append(
            (paragraph_id.strip(), text)
        )

    if not normalized_paragraphs:
        return AIEntityExtractionResult()

    prompt = _build_prompt(
        paragraphs=normalized_paragraphs,
        novel_title=novel_title,
        author=author,
    )

    raw = client.generate(prompt)
    data = extract_json(raw)

    if not isinstance(data, dict):
        raise RuntimeError(
            "Output entity extractor bukan object JSON."
        )

    raw_entities = data.get("entities", [])

    if not isinstance(raw_entities, list):
        raise RuntimeError(
            "Field 'entities' harus berupa list."
        )

    valid_paragraph_ids = {
        paragraph_id
        for paragraph_id, _ in normalized_paragraphs
    }

    entities = []

    for item in raw_entities:
        entity = _normalize_entity(item)

        if entity is None:
            continue

        if entity.source_paragraph_id not in valid_paragraph_ids:
            continue

        entities.append(entity)

    entities = _deduplicate(entities)

    return AIEntityExtractionResult(
        entities=entities
    )


def extract_entities_with_ai(
    client,
    text,
    novel_title="",
    author="",
):
    """
    Backward-compatible single-paragraph wrapper.
    """

    result = extract_entities_batch_with_ai(
        client=client,
        paragraphs=[("paragraph_0", text)],
        novel_title=novel_title,
        author=author,
    )

    return result
