from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


class TranslationCache:
    """
    Persistent cache untuk hasil translasi yang sudah tervalidasi.

    Satu cache instance hanya digunakan untuk satu project.
    Entry cache hanya dianggap valid jika statusnya 'passed'.
    """

    CACHE_VERSION = 1

    def __init__(
        self,
        cache_dir: str | Path = "cache",
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def build_key(
        source_text: str,
        paragraph_texts: list[str],
        chapter_context: dict[str, Any] | None = None,
        context_state: Any | None = None,
        entity_resolutions: list[Any] | None = None,
        model: str = "",
    ) -> str:
        """
        Membuat cache key deterministik dari seluruh input
        yang relevan terhadap hasil translasi.
        """

        normalized_context = (
            chapter_context
            if chapter_context is not None
            else {}
        )

        if context_state is None:
            normalized_state = {}
        elif hasattr(context_state, "to_dict"):
            normalized_state = context_state.to_dict()
        elif hasattr(context_state, "__dict__"):
            normalized_state = vars(context_state)
        else:
            normalized_state = context_state

        normalized_entities = (
            entity_resolutions
            if entity_resolutions is not None
            else []
        )

        payload = {
            "cache_version": TranslationCache.CACHE_VERSION,
            "source_text": source_text,
            "paragraph_texts": paragraph_texts,
            "chapter_context": normalized_context,
            "context_state": normalized_state,
            "entity_resolutions": normalized_entities,
            "model": model,
        }

        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    def _path(self, key: str) -> Path:
        if not key or "/" in key or "\\" in key:
            raise ValueError(
                "Cache key tidak valid."
            )

        return self.cache_dir / f"{key}.json"

    def _temp_path(self, key: str) -> Path:
        return (
            self.cache_dir
            / f".{key}.tmp"
        )

    def get(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        """
        Mengambil cache entry.

        Entry dengan status selain 'passed' dianggap tidak valid.
        Cache rusak tidak digunakan.
        """

        path = self._path(key)

        if not path.exists():
            return None

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except (
            OSError,
            json.JSONDecodeError,
            UnicodeDecodeError,
        ):
            return None

        if not isinstance(data, dict):
            return None

        if data.get("cache_version") != self.CACHE_VERSION:
            return None

        if data.get("status") != "passed":
            return None

        if "translation" not in data:
            return None

        return data

    def set(
        self,
        key: str,
        translation: str,
        paragraph_translations: list[str] | None = None,
        context_state: Any | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Menyimpan hasil translasi yang sudah PASS.

        Penulisan menggunakan temporary file + os.replace()
        agar entry tidak tertulis setengah-setengah.
        """

        if not isinstance(translation, str):
            raise TypeError(
                "translation harus berupa string."
            )

        if not translation.strip():
            raise ValueError(
                "translation tidak boleh kosong."
            )

        if context_state is None:
            safe_context_state = {}
        elif hasattr(context_state, "to_dict"):
            safe_context_state = context_state.to_dict()
        elif hasattr(context_state, "__dict__"):
            safe_context_state = vars(context_state)
        else:
            safe_context_state = context_state

        data = {
            "cache_version": self.CACHE_VERSION,
            "status": "passed",
            "translation": translation,
            "paragraph_translations": (
                paragraph_translations
                if paragraph_translations is not None
                else []
            ),
            "context_state": safe_context_state,
            "metadata": (
                metadata
                if metadata is not None
                else {}
            ),
        }

        path = self._path(key)
        temp_path = self._temp_path(key)

        try:
            with temp_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.flush()
                os.fsync(file.fileno())

            os.replace(
                temp_path,
                path,
            )

        except Exception:
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            raise

    def delete(
        self,
        key: str,
    ) -> bool:
        """
        Hapus satu cache entry.

        Return True jika entry memang ada dan berhasil dihapus.
        """

        path = self._path(key)

        if not path.exists():
            return False

        path.unlink()
        return True

    def clear(self) -> int:
        """
        Hapus seluruh cache entry pada project ini.

        Return jumlah entry yang dihapus.
        """

        count = 0

        for path in self.cache_dir.glob("*.json"):
            try:
                path.unlink()
                count += 1
            except OSError:
                pass

        return count
