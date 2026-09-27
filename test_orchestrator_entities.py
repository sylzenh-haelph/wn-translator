import shutil
from pathlib import Path
from types import SimpleNamespace

from models.document import Document, Paragraph, TextRun
from research.chapter_entity_service import ChapterEntityService
from translation.chapter_processor import ChapterProcessor
from translation.orchestrator import TranslationOrchestrator
from storage.progress_db import ProgressDB
from qa.retry_controller import RetryController
from translation.translation_engine import TranslationResult
from translation.chapter_context import ContextState


TEST_DIR = Path("orchestrator_entity_test")

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)


# ============================================================
# DOCUMENT
# ============================================================

document = Document(
    title="Entity Integration Test",
    author="Test Author",
)

document.paragraphs = [
    Paragraph(
        id="p0000",
        runs=[
            TextRun(
                text="Alice enters the Royal Palace."
            )
        ],
        style={
            "name": "Normal",
            "heading_level": None,
        },
    ),
    Paragraph(
        id="p0001",
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
]


# ============================================================
# FAKE ENTITY PIPELINE
#
# ChapterEntityService sekarang memanggil:
#
#     process_document(document)
#
# dan mengharapkan object yang mempunyai:
#
#     .entities
# ============================================================

class FakeEntityPipeline:

    def process_document(self, document):
        entities = []

        for paragraph in document.paragraphs:
            text = paragraph.text

            if "Alice" in text:
                entities.append(
                    {
                        "text": "Alice",
                        "entity_type": "character",
                        "source_paragraph_id": paragraph.id,
                        "translation": None,
                    }
                )

            if "Royal Palace" in text:
                entities.append(
                    {
                        "text": "Royal Palace",
                        "entity_type": "place",
                        "source_paragraph_id": paragraph.id,
                        "translation": "Istana Kerajaan",
                    }
                )

        return SimpleNamespace(
            entities=entities
        )


entity_service = ChapterEntityService(
    entity_pipeline=FakeEntityPipeline(),
)


# ============================================================
# FAKE TRANSLATION ENGINE
# ============================================================

class FakeTranslationEngine:

    def translate(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        # Pastikan entity benar-benar diteruskan
        assert entity_resolutions is not None
        assert len(entity_resolutions) == 2

        entity_texts = []

        for entity in entity_resolutions:
            if hasattr(entity, "text"):
                entity_texts.append(entity.text)

            elif isinstance(entity, dict):
                entity_texts.append(
                    entity.get("text")
                )

        assert "Alice" in entity_texts
        assert "Royal Palace" in entity_texts

        translation = (
            "Alice memasuki Istana Kerajaan.\n"
            "Marcus mengikutinya."
        )

        return TranslationResult(
            chunk_id=chunk.chunk_id,
            translation=translation,
            context_state=ContextState(
                scene="palace",
                active_characters=[
                    "Alice",
                    "Marcus",
                ],
                current_situation=(
                    "Alice enters the palace."
                ),
                references=[],
                style_state={},
            ),
            raw_response={},
        )


# ============================================================
# QA
# ============================================================

def fake_qa(
    source_text,
    translation,
    preserved_entities=None,
):
    from qa.rule_based_qa import run_qa

    return run_qa(
        source_text=source_text,
        translation=translation,
        preserved_entities=preserved_entities,
    )


# ============================================================
# BUILD PIPELINE
# ============================================================

progress_db = ProgressDB(
    progress_dir=TEST_DIR / "progress"
)

retry_controller = RetryController(
    translation_engine=FakeTranslationEngine(),
    qa_function=fake_qa,
    max_retries=2,
)

chapter_processor = ChapterProcessor(
    retry_controller=retry_controller,
    progress_db=progress_db,
)

orchestrator = TranslationOrchestrator(
    chapter_processor=chapter_processor,
    max_tokens=1000,
    entity_service=entity_service,
)


# ============================================================
# RUN
# ============================================================

print("=== ENTITY ORCHESTRATOR ===")

result = orchestrator.process_document(
    document
)

print("Document:", result.title)
print("Author:", result.author)
print("Chapters:", result.chapter_count)

chapter = result.chapters[0]

print("Entity count:", chapter.entity_count)

for entity in chapter.resolved_entities:
    if hasattr(entity, "__dict__"):
        print(entity.__dict__)
    else:
        print(entity)


# ============================================================
# ASSERTIONS
# ============================================================

assert result.title == "Entity Integration Test"
assert result.author == "Test Author"
assert result.chapter_count == 1

assert chapter.entity_count == 2

entities = {}

for entity in chapter.resolved_entities:
    if hasattr(entity, "text"):
        entities[entity.text] = entity
    elif isinstance(entity, dict):
        entities[entity["text"]] = entity

assert "Alice" in entities
assert "Royal Palace" in entities

alice = entities["Alice"]
palace = entities["Royal Palace"]

if hasattr(alice, "entity_type"):
    assert alice.entity_type == "character"
    assert alice.source_paragraph_id == "p0000"
else:
    assert alice["entity_type"] == "character"
    assert alice["source_paragraph_id"] == "p0000"

if hasattr(palace, "entity_type"):
    assert palace.entity_type == "place"
    assert palace.source_paragraph_id == "p0000"
else:
    assert palace["entity_type"] == "place"
    assert palace["source_paragraph_id"] == "p0000"


# ============================================================
# VERIFY TRANSLATION RESULT
# ============================================================

processed = chapter.processed_chunks[0]

assert processed.qa_passed is True
assert processed.flagged is False
assert processed.attempts == 1

assert (
    processed.translation
    == "Alice memasuki Istana Kerajaan.\n"
       "Marcus mengikutinya."
)


# ============================================================
# VERIFY PROGRESS
# ============================================================

progress = progress_db.load(
    "chapter_001"
)

assert progress["status"] == "completed"
assert len(progress["completed_chunks"]) == 1


print("PASS")

shutil.rmtree(TEST_DIR)
