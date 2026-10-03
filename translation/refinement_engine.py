from dataclasses import dataclass, field
from typing import Any

from translation.chapter_context import ContextState
from translation.model_client import extract_json


@dataclass
class RefinementResult:
    translation: str
    paragraph_translations: list[str] = field(
        default_factory=list
    )
    context_state: ContextState = field(
        default_factory=ContextState
    )


class RefinementEngine:
    """
    Refines an existing English -> Indonesian translation.

    Unlike TranslationEngine, this engine does not translate
    the source from scratch. It receives the previous translation
    and concrete QA issues, then asks the model to repair them.
    """

    SYSTEM_PROMPT = """You are a professional English-to-Indonesian
fiction translation editor.

Your task is to REFINE an existing Indonesian translation based on
specific QA issues.

Do NOT translate from scratch unless necessary to repair an issue.
Preserve everything that is already correct.

Preserve:
- meaning
- character voice
- narrative tone
- dialogue
- proper nouns according to entity rules
- paragraph boundaries
- correct existing wording whenever possible

IMMUTABLE PARAGRAPH RULE:
1 source paragraph MUST produce exactly 1 translated paragraph.
Never merge, split, reorder, omit, or invent paragraphs.

For every input paragraph, return exactly one item in
paragraph_translations in the same order.

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

    def refine(
        self,
        text: str,
        translation: str,
        paragraph_translations: list[str],
        chapter_context: dict[str, Any] | None = None,
        context_state: ContextState | None = None,
        entity_resolutions: list | None = None,
        qa_issues: list | None = None,
    ) -> RefinementResult:
        if not paragraph_translations:
            raise ValueError(
                "paragraph_translations tidak boleh kosong."
            )

        prompt = self._build_prompt(
            text=text,
            translation=translation,
            paragraph_translations=paragraph_translations,
            chapter_context=chapter_context or {},
            context_state=context_state or ContextState(),
            entity_resolutions=entity_resolutions or [],
            qa_issues=qa_issues or [],
        )

        raw = self.client.generate(prompt)
        data = extract_json(raw)

        refined_translation = str(
            data.get("translation", "")
        )

        refined_paragraphs = data.get(
            "paragraph_translations"
        )

        if not isinstance(refined_paragraphs, list):
            raise ValueError(
                "Model tidak mengembalikan "
                "paragraph_translations sebagai list."
            )

        refined_paragraphs = [
            str(value)
            for value in refined_paragraphs
        ]

        if len(refined_paragraphs) != len(
            paragraph_translations
        ):
            raise ValueError(
                "Jumlah paragraph_translations hasil "
                "refinement tidak sesuai: "
                f"{len(refined_paragraphs)} != "
                f"{len(paragraph_translations)}"
            )

        context_data = data.get(
            "context_state",
            {},
        )

        if not isinstance(context_data, dict):
            context_data = {}

        updated_state = ContextState(
            scene=str(
                context_data.get("scene", "")
            ),
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
                or {}
            ),
        )

        return RefinementResult(
            translation=refined_translation,
            paragraph_translations=refined_paragraphs,
            context_state=updated_state,
        )

    def _build_prompt(
        self,
        text: str,
        translation: str,
        paragraph_translations: list[str],
        chapter_context: dict[str, Any],
        context_state: ContextState,
        entity_resolutions: list,
        qa_issues: list,
    ) -> str:
        entities = []

        for entity in entity_resolutions:
            if hasattr(entity, "__dict__"):
                entities.append(entity.__dict__)
            elif isinstance(entity, dict):
                entities.append(entity)

        issues = []

        for issue in qa_issues:
            if hasattr(issue, "__dict__"):
                issues.append(issue.__dict__)
            elif isinstance(issue, dict):
                issues.append(issue)
            else:
                issues.append(str(issue))

        paragraphs = "\n".join(
            f"[PARAGRAPH {index + 1}]\n{paragraph}"
            for index, paragraph in enumerate(
                paragraph_translations
            )
        )

        return f"""{self.SYSTEM_PROMPT}

CHAPTER CONTEXT:
{chapter_context}

CURRENT CONTEXT STATE:
{context_state.to_dict()}

ENTITY RESOLUTIONS:
{entities}

QA ISSUES TO REPAIR:
{issues}

SOURCE TEXT:
{text}

CURRENT TRANSLATION:
{translation}

CURRENT PARAGRAPH TRANSLATIONS:
{paragraphs}

Refine the current translation and repair the specified QA issues.
"""
