from pathlib import Path
from types import SimpleNamespace
import shutil

from models.document import Document, Paragraph, TextRun
from translation.chapter_context import ContextState
from translation.chunker import build_chunks
from translation.chapter_processor import ChapterProcessor
from translation.chapter_translation_assembler import ChapterTranslationAssembler
from translation.chapter_reconstructor import ChapterReconstructor
from qa.retry_controller import RetryController
from storage.progress_db import ProgressDB


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

        paragraph_translations = [
            f"Terjemahan: {text}"
            for text in chunk.paragraph_texts
        ]

        translation = "\n".join(paragraph_translations)

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
            "translation": translation,
            "paragraph_translations": paragraph_translations,
            "qa_result": {
                "passed": True,
                "issues": [],
            },
            "context_state": new_state.to_dict(),
        }

        return SimpleNamespace(
            passed=True,
            translation=translation,
            paragraph_translations=paragraph_translations,
            attempts=[attempt],
            flagged=False,
            qa_result=qa_result,
            context_state=new_state,
        )


progress_dir = Path("test_pipeline_progress")

if progress_dir.exists():
    shutil.rmtree(progress_dir)

progress_db = ProgressDB(progress_dir=progress_dir)

retry_controller = FakeRetryController()

processor = ChapterProcessor(
    retry_controller=retry_controller,
    progress_db=progress_db,
)

document = Document(
    title="Pipeline Test",
    author="Test Author",
    paragraphs=[
        Paragraph(
            id="p0001",
            runs=[
                TextRun(
                    text="Alice enters the Royal Palace.",
                    formatting={"bold": True},
                )
            ],
            style={"alignment": "left"},
        ),
        Paragraph(
            id="p0002",
            runs=[
                TextRun(
                    text="Marcus follows her.",
                    formatting={"italic": True},
                )
            ],
            style={"alignment": "left"},
        ),
        Paragraph(
            id="p0003",
            runs=[
                TextRun(
                    text="They enter the main hall.",
                    formatting={},
                )
            ],
            style={"alignment": "left"},
        ),
    ],
)


print("=== BUILD CHUNKS ===")

chunks = build_chunks(
    document.paragraphs,
    max_tokens=1000,
)

print("Chunks:", len(chunks))

assert len(chunks) == 1
assert chunks[0].paragraph_ids == [
    "p0001",
    "p0002",
    "p0003",
]

print("Chunk paragraph IDs: PASS")


print("\n=== PROCESS CHAPTER ===")

chapter_context = SimpleNamespace(
    chapter_id="chapter_001",
)

results = processor.process_chapter(
    chapter_id="chapter_001",
    chunks=chunks,
    chapter_context=chapter_context,
    initial_context_state=ContextState(),
)

assert len(results) == 1

processed = results[0]

assert processed.qa_passed is True
assert processed.paragraph_translations == [
    "Terjemahan: Alice enters the Royal Palace.",
    "Terjemahan: Marcus follows her.",
    "Terjemahan: They enter the main hall.",
]

print("Processing: PASS")
print("Paragraph translations: PASS")


print("\n=== ASSEMBLE ===")

assembler = ChapterTranslationAssembler()

assembled = assembler.assemble(
    chunks=chunks,
    processed_chunks=results,
    paragraph_ids=[
        "p0001",
        "p0002",
        "p0003",
    ],
)

assert [item.paragraph_id for item in assembled] == [
    "p0001",
    "p0002",
    "p0003",
]

assert [item.translated_text for item in assembled] == [
    "Terjemahan: Alice enters the Royal Palace.",
    "Terjemahan: Marcus follows her.",
    "Terjemahan: They enter the main hall.",
]

print("Assembly order: PASS")
print("Paragraph ID mapping: PASS")


print("\n=== RECONSTRUCT ===")

translated_by_id = {
    item.paragraph_id: item.translated_text
    for item in assembled
}

translated_paragraphs = [
    translated_by_id[paragraph.id]
    for paragraph in document.paragraphs
]

reconstructor = ChapterReconstructor()

reconstructed = reconstructor.reconstruct(
    chapter_id="chapter_001",
    title="Chapter 1",
    source_paragraphs=document.paragraphs,
    translated_paragraphs=translated_paragraphs,
)

assert [p.id for p in reconstructed.paragraphs] == [
    "p0001",
    "p0002",
    "p0003",
]

assert reconstructed.paragraphs[0].text == (
    "Terjemahan: Alice enters the Royal Palace."
)

assert reconstructed.paragraphs[1].text == (
    "Terjemahan: Marcus follows her."
)

assert reconstructed.paragraphs[2].text == (
    "Terjemahan: They enter the main hall."
)

assert reconstructed.paragraphs[0].runs[0].formatting["bold"] is True
assert reconstructed.paragraphs[1].runs[0].formatting["italic"] is True

print("Paragraph reconstruction: PASS")
print("Formatting preservation: PASS")


print("\n=== PROGRESS ===")

saved = progress_db.get_chunk(
    "chapter_001",
    "chunk_0000",
)

assert saved is not None
assert saved["qa_passed"] is True
assert saved["paragraph_translations"] == processed.paragraph_translations

print("Progress persistence: PASS")


print("\n=== FINAL ===")

assert retry_controller.calls == ["chunk_0000"]

print("RetryController call count: PASS")
print("PASS")
