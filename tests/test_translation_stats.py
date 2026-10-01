from translation.chapter_processor import ProcessedChunk
from translation.chapter_context import ContextState
from storage.translation_stats import (
    ChapterStats,
    TranslationStats,
)


def test_chapter_stats():
    chunks = [
        ProcessedChunk(
            chunk_id="chunk-1",
            translation="A",
            context_state=ContextState(),
            attempts=1,
            qa_passed=True,
            flagged=False,
            cache_hit=False,
        ),
        ProcessedChunk(
            chunk_id="chunk-2",
            translation="B",
            context_state=ContextState(),
            attempts=2,
            qa_passed=True,
            flagged=True,
            cache_hit=False,
        ),
        ProcessedChunk(
            chunk_id="chunk-3",
            translation="C",
            context_state=ContextState(),
            attempts=0,
            qa_passed=True,
            flagged=False,
            cache_hit=True,
        ),
    ]

    stats = ChapterStats(
        chapter_id="chapter-1",
        title="Chapter 1: Test",
        paragraphs=5,
    )

    stats.record_chunks(chunks)

    assert stats.chunks == 3
    assert stats.completed_chunks == 3
    assert stats.qa_passed == 3
    assert stats.qa_failed == 0
    assert stats.flagged_chunks == 1

    assert stats.attempts == 3
    assert stats.retries == 1

    assert stats.cache_hits == 1
    assert stats.cache_misses == 2


def test_translation_stats_aggregation():
    stats = TranslationStats()

    chunks = [
        ProcessedChunk(
            chunk_id="chunk-1",
            translation="A",
            context_state=ContextState(),
            attempts=2,
            qa_passed=True,
            flagged=False,
            cache_hit=False,
        )
    ]

    entities = [
        type(
            "Entity",
            (),
            {"status": "researched"},
        )(),
        type(
            "Entity",
            (),
            {"status": "research_failed"},
        )(),
    ]

    chapter = stats.add_chapter(
        chapter_id="chapter-1",
        title="Chapter 1: Test",
        paragraphs=4,
        processed_chunks=chunks,
        entities=entities,
    )

    assert chapter.entities == 2
    assert chapter.research_failed == 1

    stats.mark_completed_chapter()

    assert stats.total_chapters == 1
    assert stats.completed_chapters == 1
    assert stats.total_paragraphs == 4
    assert stats.total_chunks == 1
    assert stats.completed_chunks == 1
    assert stats.entities == 2
    assert stats.research_failed == 1
    assert stats.attempts == 2
    assert stats.retries == 1

    summary = stats.summary()

    assert summary["chapters"] == 1
    assert summary["completed_chapters"] == 1
    assert summary["retries"] == 1
    assert summary["research_failed"] == 1


def test_translation_stats_save(tmp_path):
    stats = TranslationStats()

    stats.add_chapter(
        chapter_id="chapter-1",
        title="Chapter 1: Test",
        paragraphs=2,
    )

    output = tmp_path / "stats.json"

    stats.save(output)

    assert output.exists()

    content = output.read_text(
        encoding="utf-8"
    )

    assert '"total_chapters": 1' in content
    assert '"total_paragraphs": 2' in content


if __name__ == "__main__":
    test_chapter_stats()
    test_translation_stats_aggregation()

    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as directory:
        from pathlib import Path

        test_translation_stats_save(
            Path(directory)
        )

    print("TRANSLATION STATS UNIT TESTS: PASS")
