from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from types import SimpleNamespace

from models.document import Paragraph, TextRun
from translation.chunker import build_chunks
from translation.chapter_translation_assembler import ChapterTranslationAssembler


def test_split_paragraph_pieces_are_joined_back():
    text = " ".join(f"kata{i}" for i in range(400))
    paragraph = Paragraph(id="p1", runs=[TextRun(text)])

    chunks = build_chunks([paragraph], max_tokens=50)
    assert len(chunks) > 1

    processed = [SimpleNamespace(translation=chunk.text.upper()) for chunk in chunks]

    result = ChapterTranslationAssembler().assemble(
        chunks=chunks,
        processed_chunks=processed,
        paragraph_ids=["p1"],
    )

    assert result[0].translated_text == " ".join(chunk.text.upper() for chunk in chunks)
