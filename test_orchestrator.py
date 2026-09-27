import shutil
from pathlib import Path

from models.document import Paragraph, TextRun
from qa.retry_controller import RetryController
from storage.progress_db import ProgressDB
from translation.chapter_processor import ChapterProcessor
from translation.chapter_context import ContextState
from translation.orchestrator import (
    ChapterInput,
    TranslationOrchestrator,
)


class FakeTranslationEngine:
    def translate(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        from types import SimpleNamespace

        new_state = ContextState(
            scene=f"Scene {chunk.chunk_id}",
            active_characters=["Alice"],
            current_situation="Testing",
            references=[],
            style_state={},
        )

        return SimpleNamespace(
            translation=(
                f"Terjemahan {chunk.chunk_id}"
                + "\n"
                * (chunk.text.count("\n"))
            ),
            context_state=new_state,
        )


def fake_qa(
    source_text,
    translation,
    preserved_entities=None,
):
    from types import SimpleNamespace

    return SimpleNamespace(
        passed=True,
        issues=[],
    )


TEST_DIR = Path("orchestrator_test")

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)


# ----------------------------------------
# BUILD COMPONENTS
# ----------------------------------------

engine = FakeTranslationEngine()

retry_controller = RetryController(
    translation_engine=engine,
    qa_function=fake_qa,
    max_retries=2,
)

progress_db = ProgressDB(TEST_DIR)

chapter_processor = ChapterProcessor(
    retry_controller=retry_controller,
    progress_db=progress_db,
)

orchestrator = TranslationOrchestrator(
    chapter_processor=chapter_processor,
    max_tokens=1000,
)


# ----------------------------------------
# BUILD SOURCE PARAGRAPHS
# ----------------------------------------

paragraphs = [
    Paragraph(
        id="p0000",
        runs=[
            TextRun(
                text="Alice enters the palace."
            )
        ],
    ),
    Paragraph(
        id="p0001",
        runs=[
            TextRun(
                text="Marcus follows her."
            )
        ],
    ),
    Paragraph(
        id="p0002",
        runs=[
            TextRun(
                text="They search the hall."
            )
        ],
    ),
]


chapter = ChapterInput(
    chapter_id="chapter_001",
    chapter_title="The Palace",
    paragraphs=paragraphs,
    resolved_entities=[],
    character_context={
        "Alice": "protagonist",
        "Marcus": "companion",
    },
    style_state={
        "tone": "natural",
    },
)


# ----------------------------------------
# FIRST RUN
# ----------------------------------------

print("=== FIRST RUN ===")

result = orchestrator.process_chapter(
    chapter
)

print("Chapter ID:", result.chapter_id)
print("Chunk count:", result.chunk_count)
print("Status:", result.status)

for chunk in result.processed_chunks:
    print(chunk)


assert result.chapter_id == "chapter_001"
assert result.chunk_count == 1
assert result.status == "completed"

progress = progress_db.load(
    "chapter_001"
)

assert progress["status"] == "completed"
assert progress["completed_chunks"] == [
    "chunk_0000"
]


# ----------------------------------------
# RESUME
# ----------------------------------------

print("\n=== RESUME ===")

result = orchestrator.process_chapter(
    chapter
)

print("Chapter ID:", result.chapter_id)
print("Chunk count:", result.chunk_count)
print("Status:", result.status)

assert result.status == "completed"


# ----------------------------------------
# CLEANUP
# ----------------------------------------

print("\nPASS")

shutil.rmtree(TEST_DIR)
