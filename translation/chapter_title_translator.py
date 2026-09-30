from __future__ import annotations

import re

from translation.model_client import extract_json


class ChapterTitleTranslator:
    """
    Menerjemahkan judul chapter ke Bahasa Indonesia tanpa mengubah
    label 'Chapter' dan nomor chapter.

    Contoh:
        Chapter 1: The Gate
        ->
        Chapter 1: The Gate (Gerbang)
    """

    SYSTEM_PROMPT = """You are an English-to-Indonesian fiction translator.

Translate a chapter title naturally into Indonesian.

RULES:
- Keep the word "Chapter" exactly as "Chapter".
- Keep the chapter number exactly unchanged.
- Keep the original English title.
- Add the Indonesian translation in parentheses after the original title.
- Preserve named entities according to the supplied entity resolutions.
- Do not add explanations.
- Return ONLY valid JSON.

Expected JSON:
{
  "title": "Chapter 1: The Gate (Gerbang)"
}
"""

    def __init__(self, client):
        self.client = client

    def translate(
        self,
        title: str,
        entity_resolutions=None,
    ) -> str:
        if not title or not title.strip():
            raise ValueError("title tidak boleh kosong.")

        entities = []

        for entity in entity_resolutions or []:
            if hasattr(entity, "__dict__"):
                entities.append(entity.__dict__)
            elif isinstance(entity, dict):
                entities.append(entity)

        prompt = f"""{self.SYSTEM_PROMPT}

SOURCE CHAPTER TITLE:
{title}

ENTITY RESOLUTIONS:
{entities}

Translate the chapter title now.
"""

        raw = self.client.generate(prompt)
        data = extract_json(raw)

        translated_title = str(
            data.get("title", "")
        ).strip()

        if not translated_title:
            raise ValueError(
                "Model tidak mengembalikan title translation."
            )

        self._validate(title, translated_title)

        return translated_title

    @staticmethod
    def _validate(
        source_title: str,
        translated_title: str,
    ):
        source_match = re.match(
            r"^(Chapter\s+\d+\s*:\s*)(.+)$",
            source_title.strip(),
            flags=re.IGNORECASE,
        )

        if source_match is None:
            return

        prefix = source_match.group(1)

        translated_match = re.match(
            r"^(Chapter\s+\d+\s*:\s*)(.+)$",
            translated_title,
            flags=re.IGNORECASE,
        )

        if translated_match is None:
            raise ValueError(
                "Format judul hasil tidak mempertahankan "
                "'Chapter' dan nomor chapter."
            )

        source_number = re.search(
            r"\d+",
            prefix,
        ).group(0)

        translated_number = re.search(
            r"\d+",
            translated_match.group(1),
        ).group(0)

        if source_number != translated_number:
            raise ValueError(
                "Nomor chapter berubah pada hasil terjemahan."
            )

        translated_body = translated_match.group(2).strip()

        if not translated_body.endswith(")"):
            raise ValueError(
                "Judul hasil harus memiliki terjemahan "
                "Indonesia dalam tanda kurung."
            )

        opening_parenthesis = translated_body.rfind("(")

        if opening_parenthesis <= 0:
            raise ValueError(
                "Terjemahan judul dalam tanda kurung tidak ditemukan."
            )

        indonesian_title = translated_body[
            opening_parenthesis + 1:-1
        ].strip()

        if not indonesian_title:
            raise ValueError(
                "Terjemahan Indonesia pada judul kosong."
            )
