from dataclasses import dataclass

from translation.chunker import Chunk
from translation.chapter_translation_assembler import (
    ChapterTranslationAssembler,
)


@dataclass
class FakeProcessedChunk:
    translation: str
    paragraph_translations: list[str] | None = None


assembler = ChapterTranslationAssembler()

chunks = [
    Chunk(
        chunk_id="chunk_0000",
        paragraph_ids=["p0001", "p0002"],
        text="Alice enters.\nMarcus follows.",
        paragraph_texts=[
            "Alice enters.",
            "Marcus follows.",
        ],
        estimated_tokens=8,
    ),
    Chunk(
        chunk_id="chunk_0001",
        paragraph_ids=["p0003"],
        text="They continue.",
        paragraph_texts=[
            "They continue.",
        ],
        estimated_tokens=4,
    ),
]

processed = [
    FakeProcessedChunk(
        translation="Alice masuk.\nMarcus mengikuti.",
        paragraph_translations=[
            "Alice masuk.",
            "Marcus mengikuti.",
        ],
    ),
    FakeProcessedChunk(
        translation="Mereka melanjutkan.",
    ),
]

result = assembler.assemble(
    chunks=chunks,
    processed_chunks=processed,
    paragraph_ids=["p0001", "p0002", "p0003"],
)

assert [item.paragraph_id for item in result] == [
    "p0001",
    "p0002",
    "p0003",
]

assert [item.translated_text for item in result] == [
    "Alice masuk.",
    "Marcus mengikuti.",
    "Mereka melanjutkan.",
]

# Multi-paragraph chunk without paragraph-level translations must fail.
try:
    assembler.assemble(
        chunks=[
            chunks[0],
        ],
        processed_chunks=[
            FakeProcessedChunk(
                translation="Alice masuk.\nMarcus mengikuti."
            ),
        ],
        paragraph_ids=["p0001", "p0002"],
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "Multi-paragraph chunk tanpa paragraph_translations "
        "harus ditolak."
    )

# Duplicate paragraph IDs must fail.
try:
    assembler.assemble(
        chunks=[
            Chunk(
                chunk_id="chunk_duplicate",
                paragraph_ids=["p0001"],
                text="Duplicate.",
                paragraph_texts=["Duplicate."],
                estimated_tokens=3,
            ),
            Chunk(
                chunk_id="chunk_duplicate_2",
                paragraph_ids=["p0001"],
                text="Duplicate again.",
                paragraph_texts=["Duplicate again."],
                estimated_tokens=3,
            ),
        ],
        processed_chunks=[
            FakeProcessedChunk(translation="Satu."),
            FakeProcessedChunk(translation="Dua."),
        ],
        paragraph_ids=["p0001"],
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "Paragraph ID duplikat harus ditolak."
    )

# Missing paragraph must fail.
try:
    assembler.assemble(
        chunks=[
            Chunk(
                chunk_id="chunk_missing",
                paragraph_ids=["p0001"],
                text="Only one.",
                paragraph_texts=["Only one."],
                estimated_tokens=3,
            ),
        ],
        processed_chunks=[
            FakeProcessedChunk(translation="Hanya satu."),
        ],
        paragraph_ids=["p0001", "p0002"],
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "Paragraph yang hilang harus ditolak."
    )

print("=== ASSEMBLER ===")
for item in result:
    print(
        item.paragraph_id,
        "|",
        item.translated_text,
    )

print("=== CHECKS ===")
print("Multi-paragraph assembly: PASS")
print("Single-paragraph assembly: PASS")
print("Paragraph order preserved: PASS")
print("Missing paragraph validation: PASS")
print("Duplicate paragraph validation: PASS")
print("PASS")
