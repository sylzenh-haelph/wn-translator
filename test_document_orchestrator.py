import shutil
from pathlib import Path
from types import SimpleNamespace

from models.document import (
    Document,
    Paragraph,
    TextRun,
)

from qa.retry_controller import RetryController
from storage.progress_db import ProgressDB

from translation.chapter_context import (
    ContextState,
)

from translation.chapter_processor import (
    ChapterProcessor,
)

from translation.orchestrator import (
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
        new_state = ContextState(
            scene=f"Scene {chunk.chunk_id}",
            active_characters=["Alice"],
            current_situation="Testing",
            references=[],
            style_state={},
        )

        # Pertahankan jumlah paragraph.
        paragraph_count = chunk.text.count("\n") + 1

        translation = "\n".join(
            f"Terjemahan {chunk.chunk_id} p{i + 1}"
            for i in range(paragraph_count)
        )

        return SimpleNamespace(
            translation=translation,
            context_state=new_state,
        )


def fake_qa(
    source_text,
    translation,
    preserved_entities=None,
):
    return SimpleNamespace(
        passed=True,
        issues=[],
    )


TEST_DIR = Path(
    "document_orchestrator_test"
)

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)


# ----------------------------------------
# COMPONENTS
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
# DOCUMENT
# ----------------------------------------

document = Document(
    title="Test Novel",
    author="Test Author",
)

document.paragraphs = [
    Paragraph(
        id="p0000",
        runs=[
            TextRun(text="Chapter 1")
        ],
        style={
            "name": "Heading 1",
            "heading_level": 1,
        },
    ),
    Paragraph(
        id="p0001",
        runs=[
            TextRun(
                text="Alice enters the palace."
            )
        ],
        style={
            "name": "Normal",
            "heading_level": None,
        },
    ),
    Paragraph(
        id="p0002",
        runs=[
            TextRun(
                text="Marcus follows her."
            )
        ],
        style={
            "name": "Normal",
            "heading_level": None,
        },
    ),
    Paragraph(
        id="p0003",
        runs=[
            TextRun(text="Chapter 2")
        ],
        style={
            "name": "Heading 1",
            "heading_level": 1,
        },
    ),
    Paragraph(
        id="p0004",
        runs=[
            TextRun(
                text="They enter the hall."
            )
        ],
        style={
            "name": "Normal",
            "heading_level": None,
        },
    ),
]


# ----------------------------------------
# PROCESS DOCUMENT
# ----------------------------------------

print("=== PROCESS DOCUMENT ===")

result = orchestrator.process_document(
    document
)

print("Title:", result.title)
print("Author:", result.author)
print("Chapter count:", result.chapter_count)

assert result.title == "Test Novel"
assert result.author == "Test Author"
assert result.chapter_count == 2
assert len(result.chapters) == 2


# ----------------------------------------
# CHAPTER 1
# ----------------------------------------

print("\n=== CHAPTER 1 ===")

chapter_1 = result.chapters[0]

print("ID:", chapter_1.chapter_id)
print("Chunks:", chapter_1.chunk_count)
print("Status:", chapter_1.status)

for chunk in chapter_1.processed_chunks:
    print(chunk)

assert chapter_1.chapter_id == "chapter_001"
assert chapter_1.chunk_count == 1
assert chapter_1.status == "completed"


# ----------------------------------------
# CHAPTER 2
# ----------------------------------------

print("\n=== CHAPTER 2 ===")

chapter_2 = result.chapters[1]

print("ID:", chapter_2.chapter_id)
print("Chunks:", chapter_2.chunk_count)
print("Status:", chapter_2.status)

for chunk in chapter_2.processed_chunks:
    print(chunk)

assert chapter_2.chapter_id == "chapter_002"
assert chapter_2.chunk_count == 1
assert chapter_2.status == "completed"


# ----------------------------------------
# PROGRESS FILES
# ----------------------------------------

print("\n=== PROGRESS ===")

progress_1 = progress_db.load(
    "chapter_001"
)

progress_2 = progress_db.load(
    "chapter_002"
)

print("Chapter 1:", progress_1)
print("Chapter 2:", progress_2)

assert progress_1["status"] == "completed"
assert progress_2["status"] == "completed"

assert progress_1["completed_chunks"] == [
    "chunk_0000"
]

assert progress_2["completed_chunks"] == [
    "chunk_0000"
]


# ----------------------------------------
# RESUME WHOLE DOCUMENT
# ----------------------------------------

print("\n=== RESUME DOCUMENT ===")

result_2 = orchestrator.process_document(
    document
)

assert result_2.chapter_count == 2

for chapter in result_2.chapters:
    assert chapter.status == "completed"


print("\nPASS")

shutil.rmtree(TEST_DIR)
