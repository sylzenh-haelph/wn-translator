from dataclasses import dataclass, field
from typing import Any

from translation.chapter_context import ContextState
from translation.model_client import extract_json


@dataclass
class TranslationResult:
    translation: str
    paragraph_translations: list[str] = field(default_factory=list)
    context_state: ContextState = field(default_factory=ContextState)


class TranslationEngine:
    """
    English -> Indonesian fiction translation engine.

    Output contract:
    - translation: complete chunk translation
    - paragraph_translations: exactly one translation per source paragraph
    - context_state: updated lightweight chapter state
    """

    SYSTEM_PROMPT = """You are a professional English-to-Indonesian fiction translator.

Translate naturally into high-quality Indonesian while preserving:
- meaning
- character voice
- narrative tone
- dialogue
- paragraph boundaries
- proper nouns according to the supplied entity rules
- formatting intent represented by the source structure

IMMUTABLE PARAGRAPH RULE:
1 source paragraph MUST produce exactly 1 translated paragraph.
Never merge, split, reorder, omit, or invent paragraphs.

For every input paragraph, return exactly one item in
paragraph_translations in the same order.

The field translation must contain the complete translated chunk,
with paragraph boundaries represented by newline characters.

Return ONLY valid JSON with this structure:
{
  "translation": "...",
  "paragraph_translations": ["...", "..."],
  "context_state": {
    "scene": "...",
    "active_characters": [],
    "current_situation": "...",
    "references": [],
    "style_state": {}
  }
}
"""

    def __init__(self, client):
        self.client = client

    def translate(
        self,
        text: str,
        paragraph_texts: list[str],
        chapter_context: dict[str, Any] | None = None,
        context_state: ContextState | None = None,
        entity_resolutions: list | None = None,
    ) -> TranslationResult:
        if len(paragraph_texts) == 0:
            raise ValueError("paragraph_texts tidak boleh kosong.")

        prompt = self._build_prompt(
            text=text,
            paragraph_texts=paragraph_texts,
            chapter_context=chapter_context or {},
            context_state=context_state or ContextState(),
            entity_resolutions=entity_resolutions or [],
        )

        raw = self.client.generate(prompt)
        data = extract_json(raw)

        translation = str(data.get("translation", ""))

        paragraph_translations = data.get("paragraph_translations")

        if not isinstance(paragraph_translations, list):
            raise ValueError(
                "Model tidak mengembalikan paragraph_translations sebagai list."
            )

        paragraph_translations = [
            str(value)
            for value in paragraph_translations
        ]

        if len(paragraph_translations) != len(paragraph_texts):
            raise ValueError(
                "Jumlah paragraph_translations tidak sesuai: "
                f"{len(paragraph_translations)} != {len(paragraph_texts)}"
            )

        context_data = data.get("context_state", {})

        if not isinstance(context_data, dict):
            context_data = {}

        updated_state = ContextState(
            scene=str(context_data.get("scene", "")),
            active_characters=[
                str(value)
                for value in context_data.get(
                    "active_characters",
                    [],
                )
            ],
            current_situation=str(
                context_data.get(
                    "current_situation",
                    "",
                )
            ),
            references=[
                str(value)
                for value in context_data.get(
                    "references",
                    [],
                )
            ],
            style_state=dict(
                context_data.get(
                    "style_state",
                    {},
                )
            ),
        )

        return TranslationResult(
            translation=translation,
            paragraph_translations=paragraph_translations,
            context_state=updated_state,
        )

    def _build_prompt(
        self,
        text: str,
        paragraph_texts: list[str],
        chapter_context: dict[str, Any],
        context_state: ContextState,
        entity_resolutions: list,
    ) -> str:
        entities = []

        for entity in entity_resolutions:
            if hasattr(entity, "__dict__"):
                entities.append(entity.__dict__)
            elif isinstance(entity, dict):
                entities.append(entity)

        paragraphs = "\n".join(
            f"[PARAGRAPH {index + 1}]\n{paragraph}"
            for index, paragraph in enumerate(paragraph_texts)
        )

        return f"""{self.SYSTEM_PROMPT}

CHAPTER CONTEXT:
{chapter_context}

PREVIOUS CONTEXT STATE:
{context_state.to_dict()}

ENTITY RESOLUTIONS:
{entities}

SOURCE CHUNK:
{paragraphs}

Translate the source chunk now.
"""
