from dataclasses import dataclass

from translation.model_client import extract_json


@dataclass
class ResearchEvaluation:
    sufficient: bool
    confidence: float
    selected_indices: list[int]
    reason: str
    needs_more_context: bool


SYSTEM_PROMPT = """
You evaluate web search results for an entity found in fiction.

Your task is to determine whether the available search results
provide enough reliable evidence to identify the entity.

Important rules:

1. Do not invent facts.
2. Do not assume that a matching name means the result is correct.
3. Prefer results whose context clearly matches the entity.
4. If the entity is ambiguous, say that more research is needed.
5. Select only results that actually support identification.
6. A result may be irrelevant even if its title contains the entity name.

Return ONLY valid JSON:

{
  "sufficient": true,
  "confidence": 0.90,
  "selected_indices": [0, 2],
  "reason": "The selected sources clearly identify the entity.",
  "needs_more_context": false
}
"""


def evaluate_research(
    client,
    entity_text,
    entity_type,
    query,
    results,
):
    if not results:
        return ResearchEvaluation(
            sufficient=False,
            confidence=0.0,
            selected_indices=[],
            reason="No search results were returned.",
            needs_more_context=True,
        )

    formatted_results = []

    for index, result in enumerate(results):
        formatted_results.append(
            f"""
RESULT {index}

Title:
{result.title}

URL:
{result.url}

Source:
{result.source}

Snippet:
{result.snippet}
"""
        )

    prompt = f"""
{SYSTEM_PROMPT}

Entity:
{entity_text}

Expected entity type:
{entity_type}

Search query:
{query}

Search results:
{"".join(formatted_results)}
"""

    raw = client.generate(prompt)
    data = extract_json(raw)

    sufficient = bool(
        data.get("sufficient", False)
    )

    try:
        confidence = float(
            data.get("confidence", 0.0)
        )
    except (TypeError, ValueError):
        confidence = 0.0

    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    selected_indices = data.get(
        "selected_indices",
        [],
    )

    if not isinstance(selected_indices, list):
        selected_indices = []

    valid_indices = []

    for index in selected_indices:
        if isinstance(index, int) and 0 <= index < len(results):
            valid_indices.append(index)

    reason = str(
        data.get(
            "reason",
            "No reason provided.",
        )
    )

    needs_more_context = bool(
        data.get(
            "needs_more_context",
            not sufficient,
        )
    )

    return ResearchEvaluation(
        sufficient=sufficient,
        confidence=confidence,
        selected_indices=valid_indices,
        reason=reason,
        needs_more_context=needs_more_context,
    )
