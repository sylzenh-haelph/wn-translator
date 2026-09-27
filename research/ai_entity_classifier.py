from research.entity_classifier import EntityClassification
from translation.model_client import extract_json


SYSTEM_PROMPT = """
You classify entities found in English fiction.

Your task is ONLY to classify the entity.
Do not translate it.
Do not invent facts.

Allowed entity_type values:

character
place
organization
item
skill
race
title
proper_noun
unknown

Rules:

1. Use the provided context.
2. A personal name used as a person/character should be "character".
3. A named location should be "place".
4. A named organization should be "organization".
5. A named weapon, artifact, object, or special item should be "item".
6. A named ability, spell, technique, or power should be "skill".
7. A named species/type of fictional being should be "race".
8. A rank or formal designation can be "title".
9. If there is not enough evidence, use "unknown".
10. Never invent information that is not supported by the context.

Return ONLY valid JSON:

{
  "entity_type": "character",
  "confidence": 0.95,
  "reason": "Brief explanation based only on the context."
}
"""


def classify_with_ai(client, candidate, context):
    prompt = f"""
{SYSTEM_PROMPT}

Entity:
{candidate.text}

Detector type:
{candidate.entity_type}

Context:
{context}
"""

    raw = client.generate(prompt)
    data = extract_json(raw)

    entity_type = data.get("entity_type", "unknown")

    if entity_type not in {
        "character",
        "place",
        "organization",
        "item",
        "skill",
        "race",
        "title",
        "proper_noun",
        "unknown",
    }:
        entity_type = "unknown"

    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(0.0, min(1.0, confidence))

    reason = str(
        data.get(
            "reason",
            "No reason provided.",
        )
    )

    return EntityClassification(
        text=candidate.text,
        entity_type=entity_type,
        confidence=confidence,
        reason=reason,
    )
