from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json


@dataclass
class ChapterStats:
    chapter_id: str
    title: str
    paragraphs: int = 0
    chunks: int = 0
    completed_chunks: int = 0
    flagged_chunks: int = 0
    qa_passed: int = 0
    qa_failed: int = 0
    attempts: int = 0
    retries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    entities: int = 0
    research_failed: int = 0

    def record_chunks(self, processed_chunks):
        self.chunks = len(processed_chunks)

        non_cache_chunks = 0

        for chunk in processed_chunks:
            cache_hit = bool(
                getattr(chunk, "cache_hit", False)
            )

            if cache_hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1
                non_cache_chunks += 1

            if bool(
                getattr(chunk, "qa_passed", False)
            ):
                self.qa_passed += 1
                self.completed_chunks += 1
            else:
                self.qa_failed += 1

            if bool(
                getattr(chunk, "flagged", False)
            ):
                self.flagged_chunks += 1

            attempts = int(
                getattr(chunk, "attempts", 0)
            )

            if not cache_hit:
                self.attempts += attempts
                self.retries += max(
                    attempts - 1,
                    0,
                )

        # Cache hit tidak menghasilkan API attempt.
        # non_cache_chunks hanya dipakai sebagai sanity
        # reference dan sengaja tidak mengubah attempts.
        _ = non_cache_chunks


@dataclass
class TranslationStats:
    started_at: str = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        ).isoformat()
    )
    finished_at: str | None = None
    duration_seconds: float = 0.0

    total_chapters: int = 0
    completed_chapters: int = 0
    skipped_chapters: int = 0

    total_paragraphs: int = 0
    total_chunks: int = 0
    completed_chunks: int = 0
    flagged_chunks: int = 0

    qa_passed: int = 0
    qa_failed: int = 0

    attempts: int = 0
    retries: int = 0

    cache_hits: int = 0
    cache_misses: int = 0

    entities: int = 0
    research_failed: int = 0

    chapters: list[ChapterStats] = field(
        default_factory=list
    )

    def add_chapter(
        self,
        chapter_id: str,
        title: str,
        paragraphs: int,
        processed_chunks=None,
        entities=None,
    ):
        chapter = ChapterStats(
            chapter_id=chapter_id,
            title=title,
            paragraphs=paragraphs,
        )

        if processed_chunks is not None:
            chapter.record_chunks(
                processed_chunks
            )

        if entities is not None:
            chapter.entities = len(entities)

            chapter.research_failed = sum(
                1
                for entity in entities
                if str(
                    getattr(
                        entity,
                        "status",
                        "",
                    )
                ).lower()
                == "research_failed"
            )

        self.chapters.append(chapter)

        self.total_chapters = len(self.chapters)
        self.total_paragraphs += chapter.paragraphs
        self.total_chunks += chapter.chunks
        self.completed_chunks += (
            chapter.completed_chunks
        )
        self.flagged_chunks += chapter.flagged_chunks
        self.qa_passed += chapter.qa_passed
        self.qa_failed += chapter.qa_failed
        self.attempts += chapter.attempts
        self.retries += chapter.retries
        self.cache_hits += chapter.cache_hits
        self.cache_misses += chapter.cache_misses
        self.entities += chapter.entities
        self.research_failed += (
            chapter.research_failed
        )

        return chapter

    def mark_completed_chapter(self):
        self.completed_chapters += 1

    def mark_skipped_chapter(self):
        self.skipped_chapters += 1

    def finish(self, duration_seconds: float):
        self.finished_at = datetime.now(
            timezone.utc
        ).isoformat()

        self.duration_seconds = max(
            float(duration_seconds),
            0.0,
        )

    def to_dict(self):
        return asdict(self)

    def save(self, path: Path):
        path = Path(path)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = path.with_suffix(
            path.suffix + ".tmp"
        )

        with temp_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.to_dict(),
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.flush()

        temp_path.replace(path)

    def summary(self):
        return {
            "chapters": self.total_chapters,
            "completed_chapters": self.completed_chapters,
            "skipped_chapters": self.skipped_chapters,
            "paragraphs": self.total_paragraphs,
            "chunks": self.total_chunks,
            "completed_chunks": self.completed_chunks,
            "flagged_chunks": self.flagged_chunks,
            "qa_passed": self.qa_passed,
            "qa_failed": self.qa_failed,
            "attempts": self.attempts,
            "retries": self.retries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "entities": self.entities,
            "research_failed": self.research_failed,
            "duration_seconds": self.duration_seconds,
        }
