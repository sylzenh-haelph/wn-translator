from __future__ import annotations

import json
import os
import re
from pathlib import Path

from translation.model_client import extract_json


def _cache_file():
    value = os.environ.get("WN_TITLE_CACHE", "").strip()
    return Path(value) if value else None


def _load_title_cache(path):
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def _save_title_cache(path, title, translated):
    if path is None:
        return
    data = _load_title_cache(path)
    data[title] = translated
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


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

        # Judul yang hanya berisi label chapter tidak punya bagian
        # yang bisa diterjemahkan, jadi tidak perlu memanggil model.
        label_only = re.match(
            r"^Chapter\s+(\d+)$",
            title.strip(),
            flags=re.IGNORECASE,
        )
        if label_only:
            number = label_only.group(1)
            return f"Chapter {number} (Bab {number})"

        # Judul yang hanya berisi label chapter tidak punya bagian
        # yang bisa diterjemahkan, jadi tidak perlu memanggil model.
        label_only = re.match(
            r"^Chapter\s+(\d+)$",
            title.strip(),
            flags=re.IGNORECASE,
        )
        if label_only:
            number = label_only.group(1)
            return f"Chapter {number} (Bab {number})"

        # shortcut: kunci cache hanya judul asli; dua novel dengan judul sama memakai terjemahan yang sama
        cached = _load_title_cache(_cache_file()).get(title.strip())
        if cached:
            return cached

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
        _save_title_cache(_cache_file(), title.strip(), translated_title)

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

        if re.fullmatch(
            r"Chapter\s+\d+",
            indonesian_title,
            flags=re.IGNORECASE,
        ):
            raise ValueError(
                "Terjemahan Indonesia hanya berisi label chapter."
            )

        if re.fullmatch(
            r"Chapter\s+\d+",
            indonesian_title,
            flags=re.IGNORECASE,
        ):
            raise ValueError(
                "Terjemahan Indonesia hanya berisi label chapter."
            )
