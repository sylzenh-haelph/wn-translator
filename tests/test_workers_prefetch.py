from pathlib import Path
import sys
import threading

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from types import SimpleNamespace

import main
from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapter


class TwoChapterSplitter:
    def split(self, document):
        return [
            DocumentChapter(chapter_id="chapter_001", title="Chapter 1",
                            paragraphs=[Paragraph(id="p1", runs=[TextRun("SATU")])]),
            DocumentChapter(chapter_id="chapter_002", title="Chapter 2",
                            paragraphs=[Paragraph(id="p2", runs=[TextRun("DUA")])]),
        ]


class PlainTitles:
    def __init__(self, client):
        pass

    def translate(self, title, entity_resolutions=None):
        return title


class CountingProcessor:
    def __init__(self):
        self.translation_engine = SimpleNamespace(client=object())
        self.progress_db = SimpleNamespace(load=lambda chapter_id: {"status": "not_started"})
        self.calls = []
        self.lock = threading.Lock()

    def process_chapter(self, chapter_id, chunks, chapter_context, initial_context_state, entity_resolutions=None):
        with self.lock:
            self.calls.append(chapter_id)
        return [
            SimpleNamespace(
                chunk_id=c.chunk_id,
                translation="ID",
                paragraph_translations=["ID"] * len(c.paragraph_texts),
                context_state=SimpleNamespace(),
                attempts=1,
                qa_passed=True,
                flagged=False,
                issues=[],
                cache_hit=False,
            )
            for c in chunks
        ]


def run(workers, monkeypatch):
    monkeypatch.setattr(main, "DocumentChapterSplitter", lambda: TwoChapterSplitter())
    monkeypatch.setattr(main, "ChapterTitleTranslator", PlainTitles)
    processor = CountingProcessor()
    chapters, stats = main.process_chapters(
        document=Document(title="T", author="A"),
        processor=processor,
        config=SimpleNamespace(max_chunk_tokens=1000),
        workers=workers,
    )
    return chapters, stats, processor


def test_workers_two_gives_same_result_as_sequential(monkeypatch):
    seq_chapters, seq_stats, _ = run(1, monkeypatch)
    par_chapters, par_stats, par_proc = run(2, monkeypatch)
    assert [c.title for c in par_chapters] == [c.title for c in seq_chapters] == ["Chapter 1", "Chapter 2"]
    assert par_stats.summary()["completed_chapters"] == seq_stats.summary()["completed_chapters"] == 2
    assert sorted(par_proc.calls) == ["chapter_001", "chapter_002"]
