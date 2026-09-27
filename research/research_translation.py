from dataclasses import dataclass

from translation.model_client import extract_json


@dataclass
class TranslationCandidate:
    canonical_name: str
    entity_type: str
    translation_candidate: str | None
    confidence: float
    reason: str
    preserve_original: bool


class ResearchTranslationInterpreter:
    """
    Menginterpretasikan evidence hasil research untuk menentukan:
    - apakah entity diterjemahkan,
    - kandidat terjemahannya,
    - atau dipertahankan dalam bentuk asli.

    Interpreter tidak langsung memutuskan prioritas final.
    Keputusan final tetap dilakukan oleh EntityResolutionService.
    """

    def __init__(self, client):
        self.client = client

    def _build_prompt(
        self,
        entity_text,
        entity_type,
        evidence,
        project_title=None,
        chapter_context=None,
    ):
        evidence_text = []

        for index, item in enumerate(evidence, start=1):
            evidence_text.append(
                f"""Evidence {index}:
Title: {item.get("title", "")}
Source: {item.get("source", "")}
URL: {item.get("url", "")}
Snippet: {item.get("snippet", "")}
"""
            )

        evidence_block = "\n".join(evidence_text)

        return f"""
You are a terminology specialist for an English fiction-to-Indonesian translation project.

Determine how the researched entity should be handled in the Indonesian translation.

Entity: {entity_text}
Entity type: {entity_type}

Project title:
{project_title or ""}

Chapter context:
{chapter_context or ""}

Research evidence:
{evidence_block}

Rules:
1. Do not invent facts that are not supported by the evidence or context.
2. A personal fictional name should normally be preserved.
3. A named place, organization, item, skill, race, title, or other proper noun may be translated when that is appropriate.
4. Research evidence does not automatically prove that an Indonesian translation is mandatory.
5. If the correct treatment is uncertain, preserve the original.
6. Do not translate ordinary words merely because they appear in research evidence.
7. The translation candidate must be concise.
8. Return ONLY valid JSON.
9. Do not include markdown fences.
10. "preserve_original" must be true when there is no sufficiently justified translation.

Required JSON structure:
{{
  "canonical_name": "{entity_text}",
  "translation_candidate": null,
  "confidence": 0.0,
  "reason": "...",
  "preserve_original": true
}}
""".strip()

    def _generate_json(self, prompt):
        """
        Supports the real GeminiClient interface:
            client.generate() -> string JSON

        Also supports older/simple fake clients used by tests:
            client.generate_json() -> dict
        """
        generate_json = getattr(self.client, "generate_json", None)

        if callable(generate_json):
            result = generate_json(prompt)

            if not isinstance(result, dict):
                raise ValueError(
                    "Research interpreter harus mengembalikan object JSON."
                )

            return result

        generate = getattr(self.client, "generate", None)

        if not callable(generate):
            raise AttributeError(
                "Client harus menyediakan generate() atau generate_json()."
            )

        raw = generate(prompt)

        if isinstance(raw, dict):
            return raw

        if not isinstance(raw, str):
            raise ValueError(
                "Output model harus berupa string JSON atau object JSON."
            )

        return extract_json(raw)

    def interpret(
        self,
        entity_text,
        entity_type,
        evidence,
        project_title=None,
        chapter_context=None,
    ):
        prompt = self._build_prompt(
            entity_text=entity_text,
            entity_type=entity_type,
            evidence=evidence,
            project_title=project_title,
            chapter_context=chapter_context,
        )

        response = self._generate_json(prompt)

        canonical_name = response.get("canonical_name") or entity_text

        translation = response.get("translation_candidate")

        confidence = response.get("confidence", 0.0)

        reason = response.get(
            "reason",
            "",
        )

        preserve_original = response.get(
            "preserve_original",
            True,
        )

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        if translation is not None:
            translation = str(translation).strip()

            if not translation:
                translation = None

        return TranslationCandidate(
            canonical_name=str(canonical_name).strip() or entity_text,
            entity_type=entity_type,
            translation_candidate=translation,
            confidence=confidence,
            reason=str(reason),
            preserve_original=bool(preserve_original),
        )
