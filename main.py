from __future__ import annotations

import argparse
from pathlib import Path

from parsers.docx_parser import parse_docx
from parsers.epub_parser import parse_epub

from models.document import Document

from translation.chapter_splitter import DocumentChapterSplitter
from translation.chunker import build_chunks
from translation.chapter_translation_assembler import ChapterTranslationAssembler
from translation.chapter_reconstructor import ChapterReconstructor
from translation.document_assembler import DocumentAssembler
from translation.chapter_processor import ChapterProcessor
from translation.translation_engine import TranslationEngine
from translation.model_client import GeminiClient

from qa.rule_based_qa import run_qa
from qa.retry_controller import RetryController

from storage.progress_db import ProgressDB

from reconstruction.epub_reconstructor import reconstruct_epub
from reconstruction.docx_reconstructor import reconstruct_docx


def parse_document(path: str) -> Document:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"File input tidak ditemukan: {path}")

    suffix = path.suffix.lower()

    if suffix == ".epub":
        return parse_epub(path)

    if suffix == ".docx":
        return parse_docx(path)

    raise ValueError(
        f"Format belum didukung: {suffix}. Gunakan .epub atau .docx."
    )


def build_processor(progress_dir: str) -> ChapterProcessor:
    client = GeminiClient()
    translation_engine = TranslationEngine(client)

    retry_controller = RetryController(
        translation_engine=translation_engine,
        qa_function=run_qa,
        max_retries=2,
    )

    progress_db = ProgressDB(progress_dir)

    return ChapterProcessor(
        retry_controller=retry_controller,
        progress_db=progress_db,
        translation_engine=translation_engine,
        qa_checker=run_qa,
    )


def process_chapters(
    document: Document,
    progress_dir: str,
):
    splitter = DocumentChapterSplitter()
    chapters = splitter.split(document)

    processor = build_processor(progress_dir)

    chapter_results = []

    for index, chapter in enumerate(chapters, start=1):
        print(
            f"\n[{index}/{len(chapters)}] "
            f"Chapter: {chapter.title}"
        )

        chunks = build_chunks(chapter.paragraphs)

        if not chunks:
            print("  Chapter kosong, dilewati.")
            chapter_results.append(chapter)
            continue

        print(f"  Paragraph : {len(chapter.paragraphs)}")
        print(f"  Chunk     : {len(chunks)}")

        chapter_context = {
            "chapter_id": chapter.chapter_id,
            "chapter_title": chapter.title,
            "document_title": document.title,
            "author": document.author,
        }

        initial_context_state = {
            "scene": "",
            "active_characters": [],
            "current_situation": "",
            "references": [],
            "style_state": {},
        }

        processed_chunks = processor.process_chapter(
            chapter_id=chapter.chapter_id,
            chunks=chunks,
            chapter_context=chapter_context,
            initial_context_state=initial_context_state,
            entity_resolutions=None,
        )

        print(
            f"  Processed : {len(processed_chunks)} chunk"
        )

        assembler = ChapterTranslationAssembler()

        assembled = assembler.assemble(
            chunks=chunks,
            processed_chunks=processed_chunks,
            paragraph_ids=[
                paragraph.id
                for paragraph in chapter.paragraphs
            ],
        )

        translated_texts = []

        for item in assembled:
            text = getattr(item, "text", None)

            if text is None:
                text = getattr(item, "translation", None)

            if text is None:
                raise RuntimeError(
                    "ChapterTranslationAssembler menghasilkan "
                    "objek tanpa field text/translation."
                )

            translated_texts.append(text)

        if len(translated_texts) != len(chapter.paragraphs):
            raise RuntimeError(
                f"Jumlah paragraf hasil tidak cocok pada "
                f"{chapter.chapter_id}: "
                f"{len(chapter.paragraphs)} source vs "
                f"{len(translated_texts)} translated."
            )

        reconstructor = ChapterReconstructor()

        translated_chapter = reconstructor.reconstruct(
            chapter_id=chapter.chapter_id,
            title=chapter.title,
            source_paragraphs=chapter.paragraphs,
            translated_paragraphs=translated_texts,
            heading=chapter.heading,
        )

        chapter_results.append(translated_chapter)

        print("  Status    : PASS")

    return chapter_results


def assemble_document(
    source_document: Document,
    chapter_results,
):
    assembler = DocumentAssembler()

    return assembler.assemble(
        source_document=source_document,
        chapter_results=chapter_results,
    )


def reconstruct_output(
    source_path: str,
    output_path: str,
    translated_document,
):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = output_path.suffix.lower()

    if suffix == ".epub":
        reconstruct_epub(
            translated_document,
            output_path,
            source_path=source_path,
        )
        return

    if suffix == ".docx":
        reconstruct_docx(
            translated_document,
            output_path,
        )
        return

    raise ValueError(
        f"Format output belum didukung: {suffix}. "
        "Gunakan .epub atau .docx."
    )


def main():
    parser = argparse.ArgumentParser(
        description="WN Translator — automatic chapter-by-chapter translator"
    )

    parser.add_argument(
        "input",
        help="File sumber .epub atau .docx",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="File output .epub atau .docx",
    )

    parser.add_argument(
        "--project-dir",
        default=".",
        help="Direktori project",
    )

    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    project_dir = Path(args.project_dir).resolve()

    progress_dir = project_dir / "progress"

    print("=" * 60)
    print("WN TRANSLATOR")
    print("=" * 60)

    print(f"Input    : {input_path}")
    print(f"Output   : {output_path}")
    print(f"Progress : {progress_dir}")

    print("\n[1/4] Parsing document...")
    document = parse_document(str(input_path))

    print(f"  Title  : {document.title}")
    print(f"  Author : {document.author}")
    print(f"  Paras  : {len(document.paragraphs)}")
    print("  PASS")

    print("\n[2/4] Translating chapters...")
    chapter_results = process_chapters(
        document=document,
        progress_dir=str(progress_dir),
    )

    print("\n[3/4] Assembling translated document...")
    translated_document = assemble_document(
        source_document=document,
        chapter_results=chapter_results,
    )

    print(
        f"  Paragraphs hasil: "
        f"{len(translated_document.paragraphs)}"
    )
    print("  PASS")

    print("\n[4/4] Reconstructing output...")
    reconstruct_output(
        source_path=str(input_path),
        output_path=str(output_path),
        translated_document=translated_document,
    )

    print("  PASS")

    print("\n" + "=" * 60)
    print("TRANSLATION SELESAI")
    print("=" * 60)
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
