from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path


def _json_safe(value):
    """
    Convert project objects into JSON-safe values.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Path):
        return str(value)

    if is_dataclass(value):
        return _json_safe(asdict(value))

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())

    if hasattr(value, "__dict__"):
        return _json_safe(vars(value))

    return str(value)


class ProgressDB:
    def __init__(self, progress_dir="progress"):
        self.progress_dir = Path(progress_dir)
        self.progress_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, chapter_id):
        return self.progress_dir / f"{chapter_id}.json"

    def _temp_path(self, chapter_id):
        return self.progress_dir / f".{chapter_id}.tmp"

    def _backup_path(self, chapter_id):
        return self.progress_dir / f"{chapter_id}.json.bak"

    def _empty_progress(self, chapter_id):
        return {
            "chapter_id": chapter_id,
            "status": "not_started",
            "chunks": {},
            "completed_chunks": [],
            "flagged_chunks": [],
        }

    @staticmethod
    def _validate_progress(data, chapter_id):
        if not isinstance(data, dict):
            raise ValueError(
                "Progress root harus berupa object JSON."
            )

        if data.get("chapter_id") != chapter_id:
            raise ValueError(
                "chapter_id pada progress tidak cocok."
            )

        status = data.get("status")

        if status not in {
            "not_started",
            "in_progress",
            "completed",
        }:
            raise ValueError(
                f"Status progress tidak valid: {status!r}"
            )

        if not isinstance(data.get("chunks"), dict):
            raise ValueError(
                "Field 'chunks' harus berupa object."
            )

        if not isinstance(data.get("completed_chunks"), list):
            raise ValueError(
                "Field 'completed_chunks' harus berupa list."
            )

        if not isinstance(data.get("flagged_chunks"), list):
            raise ValueError(
                "Field 'flagged_chunks' harus berupa list."
            )

        return data

    def _load_file(self, path, chapter_id):
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return self._validate_progress(
            data,
            chapter_id,
        )

    def load(self, chapter_id):
        path = self._path(chapter_id)

        if not path.exists():
            backup = self._backup_path(chapter_id)

            if backup.exists():
                return self._load_file(
                    backup,
                    chapter_id,
                )

            return self._empty_progress(chapter_id)

        try:
            return self._load_file(
                path,
                chapter_id,
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
            ValueError,
            OSError,
        ) as primary_error:

            backup = self._backup_path(chapter_id)

            if backup.exists():
                try:
                    restored = self._load_file(
                        backup,
                        chapter_id,
                    )

                    print(
                        f"  WARNING: progress {chapter_id} "
                        f"rusak; menggunakan backup."
                    )

                    return restored

                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    ValueError,
                    OSError,
                ):
                    pass

            raise RuntimeError(
                f"Progress chapter {chapter_id} tidak dapat "
                f"dibaca dan backup juga tidak tersedia/valid."
            ) from primary_error

    def save(self, chapter_id, data):
        self.progress_dir.mkdir(parents=True, exist_ok=True)
        path = self._path(chapter_id)
        temp_path = self._temp_path(chapter_id)
        backup_path = self._backup_path(chapter_id)

        safe_data = _json_safe(data)

        self._validate_progress(
            safe_data,
            chapter_id,
        )

        try:
            with temp_path.open(
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    safe_data,
                    file,
                    ensure_ascii=False,
                    indent=2,
                )
                file.flush()
                os.fsync(file.fileno())

            if path.exists():
                os.replace(path, backup_path)

            os.replace(temp_path, path)

            # Pastikan directory entry juga tersinkronisasi
            # jika filesystem mendukung fsync pada directory.
            try:
                dir_fd = os.open(
                    self.progress_dir,
                    os.O_RDONLY,
                )

                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)

            except OSError:
                # Beberapa filesystem Android tidak mengizinkan
                # fsync directory. File utama tetap sudah atomic.
                pass

        except Exception:
            # Jangan meninggalkan temporary state jika save gagal.
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except OSError:
                pass

            raise

    def start_chapter(self, chapter_id):
        data = self.load(chapter_id)

        if data["status"] == "not_started":
            data["status"] = "in_progress"
            self.save(chapter_id, data)

        return data

    def save_chunk(
        self,
        chapter_id,
        chunk_id,
        translation,
        context_state,
        attempts,
        qa_passed,
        flagged=False,
        qa_issues=None,
        paragraph_translations=None,
        cache_hit=False,
    ):
        data = self.load(chapter_id)
        data["status"] = "in_progress"

        data["chunks"][chunk_id] = {
            "chunk_id": chunk_id,
            "translation": translation,
            "paragraph_translations": (
                list(paragraph_translations)
                if paragraph_translations is not None
                else []
            ),
            "context_state": _json_safe(context_state),
            "attempts": attempts,
            "qa_passed": qa_passed,
            "flagged": flagged,
            "qa_issues": _json_safe(
                qa_issues or []
            ),
            "cache_hit": bool(cache_hit),
        }

        if (
            qa_passed
            and chunk_id not in data["completed_chunks"]
        ):
            data["completed_chunks"].append(chunk_id)

        if (
            flagged
            and chunk_id not in data["flagged_chunks"]
        ):
            data["flagged_chunks"].append(chunk_id)

        self.save(chapter_id, data)

        return data

    def mark_completed(self, chapter_id):
        data = self.load(chapter_id)
        data["status"] = "completed"
        self.save(chapter_id, data)
        return data

    def is_chunk_completed(self, chapter_id, chunk_id):
        data = self.load(chapter_id)
        return chunk_id in data["completed_chunks"]

    def get_chunk(self, chapter_id, chunk_id):
        data = self.load(chapter_id)
        return data["chunks"].get(chunk_id)

    def get_next_chunk_id(self, chapter_id, chunk_ids):
        data = self.load(chapter_id)
        completed = set(data["completed_chunks"])

        for chunk_id in chunk_ids:
            if chunk_id not in completed:
                return chunk_id

        return None
