import shutil
from pathlib import Path
from types import SimpleNamespace

from storage.progress_db import ProgressDB
from translation.chapter_context import ContextState
from translation.chapter_processor import ChapterProcessor


TEST_DIR = Path("chapter_processor_test")

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)


class FakeRetryController:
    def __init__(self):
        self.calls = []

    def translate_with_retry(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        self.calls.append(chunk.chunk_id)

        new_state = ContextState(
            scene=f"Scene {chunk.chunk_id}",
            active_characters=["Alice"],
            current_situation=f"Situation {chunk.chunk_id}",
            references=[],
            style_state={},
        )

        qa_result = SimpleNamespace(
            passed=True,
            issues=[],
        )

        attempt = {
            "attempt_number": 1,
            "translation": f"Terjemahan {chunk.chunk_id}",
            "qa_result": {"passed": True, "issues": []},
            "context_state": new_state.to_dict(),
        }

        return SimpleNamespace(
            passed=True,
            translation=f"Terjemahan {chunk.chunk_id}",
            attempts=[attempt],
            flagged=False,
            qa_result=qa_result,
            context_state=new_state,
        )


class FakeChunk:
    def __init__(self, chunk_id):
        self.chunk_id = chunk_id
        self.text = f"Source {chunk_id}"


chunks = [
    FakeChunk("chunk_0000"),
    FakeChunk("chunk_0001"),
    FakeChunk("chunk_0002"),
]


chapter_context = {
    "chapter_id": "chapter_001",
    "chapter_title": "Test Chapter",
}


retry_controller = FakeRetryController()
progress_db = ProgressDB(TEST_DIR)

processor = ChapterProcessor(
    retry_controller=retry_controller,
    progress_db=progress_db,
)


print("=== FIRST RUN ===")

results = processor.process_chapter(
    chapter_id="chapter_001",
    chunks=chunks,
    chapter_context=chapter_context,
    initial_context_state=ContextState(),
)

print("Results:")

for result in results:
    print(result)


assert len(results) == 3
assert retry_controller.calls == [
    "chunk_0000",
    "chunk_0001",
    "chunk_0002",
]

progress = progress_db.load("chapter_001")

assert progress["status"] == "completed"
assert progress["completed_chunks"] == [
    "chunk_0000",
    "chunk_0001",
    "chunk_0002",
]


print("\n=== RESUME TEST ===")

retry_controller.calls.clear()

results = processor.process_chapter(
    chapter_id="chapter_001",
    chunks=chunks,
    chapter_context=chapter_context,
    initial_context_state=ContextState(),
)

print("Results:")

for result in results:
    print(result)


assert retry_controller.calls == []

assert len(results) == 3

print("\nPASS")

shutil.rmtree(TEST_DIR)
