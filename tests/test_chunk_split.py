from pathlib import Path
from types import SimpleNamespace
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from translation.chapter_context import ContextState
from translation.chapter_processor import ChapterProcessor
from translation.chunker import Chunk


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


class SplittingRetry:
    def translate_with_retry(self, chunk, chapter_context, context_state, entity_resolutions):
        if len(chunk.paragraph_ids) > 2:
            raise ValueError("Jumlah paragraph_translations tidak sesuai: 3 != 4")
        return SimpleNamespace(
            translation="\n".join(f"terjemahan {p}" for p in chunk.paragraph_ids),
            paragraph_translations=[f"terjemahan {p}" for p in chunk.paragraph_ids],
            context_state=ContextState(),
            flagged=False,
            passed=True,
            attempts=[1],
            history=[],
        )


def test_mismatched_chunk_is_split_and_completes():
    progress = FakeProgress()
    processor = ChapterProcessor(SplittingRetry(), progress)
    chunk = Chunk(
        chunk_id="chunk_0000",
        paragraph_ids=["p1", "p2", "p3", "p4"],
        text="a\nb\nc\nd",
        paragraph_texts=["a", "b", "c", "d"],
        estimated_tokens=4,
    )
    results = processor.process_chapter("chapter_008", [chunk], {}, None)
    assert len(results) == 1
    assert results[0].chunk_id == "chunk_0000"
    assert results[0].paragraph_translations == [
        "terjemahan p1", "terjemahan p2", "terjemahan p3", "terjemahan p4",
    ]
    assert results[0].qa_passed is True
    assert progress.completed == "chapter_008"
