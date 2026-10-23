from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.chapter_processor import ChapterProcessor


class FakeProgress:
    def __init__(self):
        self.saved = []
        self.completed = None

    def load(self, chapter_id):
        return {"chunks": {}}

    def save_chunk(self, **kwargs):
        self.saved.append(kwargs)

    def mark_completed(self, chapter_id):
        self.completed = chapter_id

    def start_chapter(self, chapter_id):
        pass


class NoCallRetry:
    def translate_with_retry(self, **kwargs):
        raise AssertionError("chunk kosong tidak boleh dikirim ke model")


def test_blank_chunk_skips_model_and_marks_chapter_completed():
    progress = FakeProgress()
    processor = ChapterProcessor(NoCallRetry(), progress)
    chunks = [
        SimpleNamespace(chunk_id="chunk_0000", paragraph_ids=["p1"], paragraph_texts=[""], text=""),
    ]
    results = processor.process_chapter("chapter_001", chunks, {}, None)
    assert results[0].translation == ""
    assert results[0].paragraph_translations == [""]
    assert results[0].qa_passed is True
    assert progress.completed == "chapter_001"
    assert progress.saved[0]["chunk_id"] == "chunk_0000"
