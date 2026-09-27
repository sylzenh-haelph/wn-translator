import json
import os
from pathlib import Path


class ProgressDB:
    def __init__(self, progress_dir="progress"):
        self.progress_dir = Path(progress_dir)
        self.progress_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _path(self, chapter_id):
        return self.progress_dir / f"{chapter_id}.json"

    def _empty_progress(self, chapter_id):
        return {
            "chapter_id": chapter_id,
            "status": "not_started",
            "chunks": {},
            "completed_chunks": [],
            "flagged_chunks": [],
        }

    def load(self, chapter_id):
        path = self._path(chapter_id)

        if not path.exists():
            return self._empty_progress(chapter_id)

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        # Migrasi ringan untuk progress file lama.
        data.setdefault("chapter_id", chapter_id)
        data.setdefault("status", "not_started")
        data.setdefault("chunks", {})
        data.setdefault("completed_chunks", [])
        data.setdefault("flagged_chunks", [])

        return data

    def save(self, chapter_id, data):
        path = self._path(chapter_id)
        temp_path = path.with_suffix(".tmp")

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

        os.replace(temp_path, path)

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
            "context_state": context_state,
            "attempts": attempts,
            "qa_passed": qa_passed,
            "flagged": flagged,
            "qa_issues": qa_issues or [],
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
