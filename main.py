from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from config.settings import load_config
from parsers.docx_parser import parse_docx
from parsers.epub_parser import parse_epub
from reconstruction.docx_reconstructor import reconstruct_docx
from reconstruction.epub_reconstructor import reconstruct_epub
from reconstruction.epub_validator import validate_epub
from research.runtime import build_research_service
from storage.logger import ProjectLogger
from storage.progress_db import ProgressDB
from translation.chapter_reconstructor import ChapterReconstructor
from translation.chapter_splitter import DocumentChapterSplitter
from translation.chapter_title_translator import ChapterTitleTranslator
from translation.chapter_translation_assembler import ChapterTranslationAssembler
from translation.chunker import build_chunks
from translation.document_assembler import DocumentAssembler
from translation.runtime import build_chapter_processor


SUPPORTED_INPUTS = {".epub", ".docx"}
SUPPORTED_OUTPUTS = {".epub", ".docx"}


def parse_document(path: Path):
    suffix = path.suffix.lower()

    if suffix == ".epub":
        return parse_epub(path)

    if suffix == ".docx":
        return parse_docx(path)

    raise ValueError(
        f"Format input tidak didukung: {suffix}"
    )


def validate_paths(
    input_path: Path,
    output_path: Path,
    project_dir: Path,
):
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input tidak ditemukan: {input_path}"
        )

    if not input_path.is_file():
        raise ValueError(
            f"Input bukan file: {input_path}"
        )

    if input_path.suffix.lower() not in SUPPORTED_INPUTS:
        raise ValueError(
            f"Format input tidak didukung: "
            f"{input_path.suffix}"
        )

    if output_path.suffix.lower() not in SUPPORTED_OUTPUTS:
        raise ValueError(
            f"Format output tidak didukung: "
            f"{output_path.suffix}"
        )

    if input_path.resolve() == output_path.resolve():
        raise ValueError(
            "Input dan output tidak boleh file yang sama."
        )

    project_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


def create_safe_output_path(output_path: Path):
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix=".wn-translator-",
            dir=output_path.parent,
        )
    )

    return (
        temp_dir,
        temp_dir / output_path.name,
    )


def validate_output(
    output_path: Path,
    logger: ProjectLogger | None = None,
):
    if not output_path.exists():
        raise RuntimeError(
            f"Output tidak ditemukan: {output_path}"
        )

    if not output_path.is_file():
        raise RuntimeError(
            f"Output bukan file: {output_path}"
        )

    size = output_path.stat().st_size

    if size == 0:
        raise RuntimeError(
            "Output berukuran 0 byte."
        )

    message = f"Output size: {size:,} bytes"

    print(f"  {message}")

    if logger:
        logger.info(message)

    if output_path.suffix.lower() == ".epub":
        result = validate_epub(output_path)

        if not result.passed:
            print("  EPUB validation: FAIL")

            if logger:
                logger.error(
                    "EPUB validation: FAIL"
                )

            for issue in result.issues:
                message = (
                    f"[{issue.severity.upper()}] "
                    f"{issue.rule}: {issue.message}"
                )

                print(f"    {message}")

                if logger:
                    logger.error(message)

            raise RuntimeError(
                "Output EPUB gagal validasi."
            )

        print("  EPUB validation: PASS")

        if logger:
            logger.info(
                "EPUB validation: PASS"
            )


def reconstruct_output(
    input_path: Path,
    translated_document,
    output_path: Path,
):
    suffix = output_path.suffix.lower()

    if suffix == ".epub":
        reconstruct_epub(
            translated_document,
            output_path,
            source_path=input_path,
        )
        return

    if suffix == ".docx":
        reconstruct_docx(
            translated_document,
            output_path,
        )
        return

    raise ValueError(
        f"Format output tidak didukung: {suffix}"
    )


def process_chapters(
    document,
    processor,
    config,
    logger: ProjectLogger | None = None,
    entity_service=None,
):
    splitter = DocumentChapterSplitter()
    chapters = splitter.split(document)

    assembler = ChapterTranslationAssembler()
    reconstructor = ChapterReconstructor()
    title_translator = ChapterTitleTranslator(processor.translation_engine.client)

    translated_chapters = []

    print()
    print("[2/4] Translating chapters...")

    if logger:
        logger.info(
            f"Translation started: "
            f"{len(chapters)} chapters"
        )

    for index, chapter in enumerate(
        chapters,
        start=1,
    ):
        print()
        print(
            f"[{index}/{len(chapters)}] "
            f"Chapter: {chapter.title}"
        )

        if logger:
            logger.info(
                f"Chapter started: "
                f"{chapter.chapter_id} | "
                f"{chapter.title}"
            )

        if not chapter.paragraphs:
            print(
                "  Chapter kosong, dilewati."
            )

            if logger:
                logger.info(
                    f"Chapter skipped (empty): "
                    f"{chapter.chapter_id}"
                )

            bilingual_title = title_translator.translate(
                title=chapter.title,
                entity_resolutions=[],
            )
            chapter.translated_title = bilingual_title

            print(
                f"  Title     : {bilingual_title}"
            )

            if logger:
                logger.info(
                    f"Chapter title translated: "
                    f"{chapter.chapter_id} | "
                    f"{bilingual_title}"
                )

            translated_chapters.append(
                reconstructor.reconstruct(
                    chapter_id=chapter.chapter_id,
                    title=bilingual_title,
                    source_paragraphs=[],
                    translated_paragraphs=[],
                    heading=chapter.heading,
                )
            )

            continue

        print(
            f"  Paragraph : "
            f"{len(chapter.paragraphs)}"
        )

        if logger:
            logger.info(
                f"Chapter paragraphs: "
                f"{chapter.chapter_id} | "
                f"{len(chapter.paragraphs)}"
            )

        # --------------------------------------------------
        # ENTITY RESEARCH
        # --------------------------------------------------

        resolved_entities = []

        if entity_service is not None:
            print("  Research  : analyzing entities...")

            if logger:
                logger.info(
                    f"Entity research started: "
                    f"{chapter.chapter_id}"
                )

            entity_result = entity_service.process_chapter(
                chapter_id=chapter.chapter_id,
                paragraphs=chapter.paragraphs,
            )

            resolved_entities = list(
                entity_result.entities
            )

            print(
                f"  Entities  : "
                f"{len(resolved_entities)}"
            )

            if logger:
                logger.info(
                    f"Entity research completed: "
                    f"{chapter.chapter_id} | "
                    f"entities={len(resolved_entities)}"
                )

                for entity in resolved_entities:
                    logger.info(
                        "Entity result: "
                        f"{chapter.chapter_id} | "
                        f"{entity.text} | "
                        f"type={entity.entity_type} | "
                        f"status={entity.status} | "
                        f"source={entity.source}"
                    )

        bilingual_title = title_translator.translate(
            title=chapter.title,
            entity_resolutions=resolved_entities,
        )
        chapter.translated_title = bilingual_title

        print(
            f"  Title     : {bilingual_title}"
        )

        if logger:
            logger.info(
                f"Chapter title translated: "
                f"{chapter.chapter_id} | "
                f"{bilingual_title}"
            )

        chunks = build_chunks(
            chapter.paragraphs,
            max_tokens=config.max_chunk_tokens,
        )

        print(
            f"  Chunk     : {len(chunks)}"
        )

        if logger:
            logger.info(
                f"Chapter chunks: "
                f"{chapter.chapter_id} | "
                f"{len(chunks)}"
            )

        chapter_context = {
            "chapter_id": chapter.chapter_id,
            "chapter_title": chapter.title,
            "document_title": document.title,
            "author": document.author,
        }

        result = processor.process_chapter(
            chapter_id=chapter.chapter_id,
            chunks=chunks,
            chapter_context=chapter_context,
            initial_context_state=None,
            entity_resolutions=resolved_entities,
        )

        print(
            f"  Processed : {len(result)} chunk"
            f"{'' if len(result) == 1 else 's'}"
        )

        if logger:
            logger.info(
                f"Chapter processed: "
                f"{chapter.chapter_id} | "
                f"{len(result)} chunks"
            )

            for processed in result:
                status = (
                    "FLAGGED"
                    if processed.flagged
                    else "PASS"
                )

                cache_status = (
                    "CACHE HIT"
                    if processed.cache_hit
                    else "CACHE MISS"
                )

                logger.info(
                    f"Chunk result: "
                    f"{processed.chunk_id} | "
                    f"{status} | "
                    f"{cache_status} | "
                    f"attempts={processed.attempts}"
                )

        assembled = assembler.assemble(
            chunks=chunks,
            processed_chunks=result,
            paragraph_ids=[
                paragraph.id
                for paragraph in chapter.paragraphs
            ],
        )

        translated_map = {
            item.paragraph_id:
            item.translated_text
            for item in assembled
        }

        translated_paragraphs = [
            translated_map[paragraph.id]
            for paragraph in chapter.paragraphs
        ]

        translated_chapters.append(
            reconstructor.reconstruct(
                chapter_id=chapter.chapter_id,
                title=bilingual_title,
                source_paragraphs=chapter.paragraphs,
                translated_paragraphs=translated_paragraphs,
                heading=chapter.heading,
            )
        )

        if logger:
            logger.info(
                f"Chapter completed: "
                f"{chapter.chapter_id}"
            )

    return translated_chapters


def show_status(input_path: Path, project_dir: Path):
    """Display translation progress without running translation."""
    if not input_path.exists():
        raise FileNotFoundError(
            f"Input tidak ditemukan: {input_path}"
        )

    if not input_path.is_file():
        raise ValueError(
            f"Input bukan file: {input_path}"
        )

    if input_path.suffix.lower() not in SUPPORTED_INPUTS:
        raise ValueError(
            f"Format input tidak didukung: {input_path.suffix}"
        )

    config = load_config(project_dir=project_dir)

    progress_path = Path(config.progress_dir)
    if not progress_path.is_absolute():
        progress_path = project_dir / progress_path

    document = parse_document(input_path)
    chapters = DocumentChapterSplitter().split(document)
    progress_db = ProgressDB(progress_path)

    print("=" * 60)
    print("WN TRANSLATOR STATUS")
    print("=" * 60)
    print(f"Novel  : {document.title}")
    print(f"Author : {document.author}")
    print(f"Input  : {input_path}")
    print(f"Project: {project_dir}")
    print(f"Progress: {progress_path}")
    print()

    completed = 0
    in_progress = 0
    not_started = 0

    for index, chapter in enumerate(chapters, start=1):
        data = progress_db.load(chapter.chapter_id)
        status = data["status"]

        chunks = data.get("chunks", {})
        completed_chunks = data.get("completed_chunks", [])
        flagged_chunks = data.get("flagged_chunks", [])

        if status == "completed":
            completed += 1
        elif status == "in_progress":
            in_progress += 1
        else:
            not_started += 1

        print(f"[{index}/{len(chapters)}] {chapter.title}")
        print(f"  Status  : {status}")
        print(
            f"  Chunks  : "
            f"{len(completed_chunks)}/{len(chunks)} completed"
        )
        print(f"  Flagged : {len(flagged_chunks)}")
        print()

    print("-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"Completed   : {completed}")
    print(f"In progress : {in_progress}")
    print(f"Not started : {not_started}")
    print(f"Total       : {len(chapters)}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="WN Translator"
    )

    parser.add_argument(
        "input",
        help="Path file EPUB/DOCX sumber",
    )

    parser.add_argument(
        "-o",
        "--output",
        required=False,
        help="Path file EPUB/DOCX hasil",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="Tampilkan status progress tanpa menjalankan translation",
    )

    parser.add_argument(
        "--project-dir",
        default="./project",
        help="Direktori project",
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Override model Gemini",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Override retry Gemini",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Override timeout request Gemini",
    )

    parser.add_argument(
        "--backoff-base",
        type=float,
        default=None,
        help="Override base backoff Gemini",
    )

    parser.add_argument(
        "--max-chunk-tokens",
        type=int,
        default=None,
        help="Override batas token chunk",
    )

    parser.add_argument(
        "--qa-max-retries",
        type=int,
        default=None,
        help="Override retry QA",
    )

    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Override direktori translation cache",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = (
        Path(args.output)
        if args.output is not None
        else None
    )
    project_dir = Path(args.project_dir)

    if args.status:
        try:
            show_status(
                input_path=input_path,
                project_dir=project_dir,
            )
        except Exception as exc:
            print(f"ERROR: {exc}")
            raise SystemExit(1)

        return

    if output_path is None:
        parser.error(
            "--output/-o wajib diisi kecuali menggunakan --status"
        )

    logger = ProjectLogger(
        log_dir=project_dir / "logs"
    )

    print("=" * 60)
    print("WN TRANSLATOR")
    print("=" * 60)

    try:
        logger.info("=" * 60)
        logger.info(
            "WN TRANSLATOR RUN STARTED"
        )

        logger.info(
            f"Input: {input_path}"
        )

        logger.info(
            f"Output: {output_path}"
        )

        validate_paths(
            input_path,
            output_path,
            project_dir,
        )

        config_overrides = {}

        if args.model is not None:
            config_overrides["model"] = args.model

        if args.max_retries is not None:
            config_overrides["max_retries"] = (
                args.max_retries
            )

        if args.timeout is not None:
            config_overrides["timeout"] = (
                args.timeout
            )

        if args.backoff_base is not None:
            config_overrides["backoff_base"] = (
                args.backoff_base
            )

        if args.max_chunk_tokens is not None:
            config_overrides["max_chunk_tokens"] = (
                args.max_chunk_tokens
            )

        if args.qa_max_retries is not None:
            config_overrides["qa_max_retries"] = (
                args.qa_max_retries
            )

        if args.cache_dir is not None:
            config_overrides["cache_dir"] = (
                args.cache_dir
            )

        config = load_config(
            project_dir=project_dir,
            overrides=config_overrides,
        )

        progress_path = (
            project_dir / config.progress_dir
        )

        cache_path = Path(
            config.cache_dir
        )

        if not cache_path.is_absolute():
            cache_path = (
                project_dir / cache_path
            )

        print(
            f"Input    : {input_path}"
        )

        print(
            f"Output   : {output_path}"
        )

        print(
            f"Progress : {progress_path}"
        )

        print(
            f"Cache    : {cache_path}"
        )

        print(
            f"Research : "
            f"{'ENABLED' if config.research_enabled else 'DISABLED'}"
        )

        logger.info(
            f"Progress: {progress_path}"
        )

        logger.info(
            f"Cache: {cache_path}"
        )

        logger.info(
            f"Config: model={config.model!r} | "
            f"max_retries={config.max_retries} | "
            f"timeout={config.timeout} | "
            f"backoff_base={config.backoff_base} | "
            f"max_chunk_tokens="
            f"{config.max_chunk_tokens} | "
            f"qa_max_retries="
            f"{config.qa_max_retries} | "
            f"research_enabled="
            f"{config.research_enabled} | "
            f"qa_enabled="
            f"{config.qa_enabled}"
        )

        print()
        print(
            "[1/4] Parsing document..."
        )

        logger.info(
            "Parsing started"
        )

        document = parse_document(
            input_path
        )

        print(
            f"  Title  : {document.title}"
        )

        print(
            f"  Author : {document.author}"
        )

        print(
            f"  Paras  : "
            f"{len(document.paragraphs)}"
        )

        print("  PASS")

        logger.info(
            f"Parsing completed | "
            f"title={document.title!r} | "
            f"author={document.author!r} | "
            f"paragraphs={len(document.paragraphs)}"
        )

        processor = build_chapter_processor(
            progress_path,
            config=config,
        )

        # --------------------------------------------------
        # RESEARCH SERVICE
        # --------------------------------------------------

        entity_service = None

        if config.research_enabled:
            print()
            print(
                "Initializing entity research..."
            )

            logger.info(
                "Entity research initialization started"
            )

            # Research menggunakan Gemini client terpisah
            # tetapi konfigurasi model/API sama dengan
            # translation runtime.
            from translation.model_client import GeminiClient

            research_client = GeminiClient(
                model=config.model,
                api_key=config.gemini_api_key,
                max_retries=config.max_retries,
                timeout=config.timeout,
                backoff_base=config.backoff_base,
            )

            entity_service = build_research_service(
                project_dir=project_dir,
                client=research_client,
                document_title=document.title,
                author=document.author,
                research_timeout=config.timeout,
            )

            logger.info(
                "Entity research initialization completed"
            )

        translated_chapters = process_chapters(
            document,
            processor,
            config,
            logger=logger,
            entity_service=entity_service,
        )

        print()
        print(
            "[3/4] Assembling document..."
        )

        logger.info(
            "Document assembly started"
        )

        document_assembler = (
            DocumentAssembler()
        )

        translated_document = (
            document_assembler.assemble(
                document,
                translated_chapters,
            )
        )

        print("  PASS")

        logger.info(
            "Document assembly completed"
        )

        print()
        print(
            "[4/4] Generating output..."
        )

        logger.info(
            "Output generation started"
        )

        temp_dir, temp_output = (
            create_safe_output_path(
                output_path
            )
        )

        try:
            reconstruct_output(
                input_path,
                translated_document,
                temp_output,
            )

            print(
                "  Validating temporary output..."
            )

            logger.info(
                "Temporary output validation started"
            )

            validate_output(
                temp_output,
                logger=logger,
            )

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(temp_output),
                str(output_path),
            )

            print(
                "  Output committed safely."
            )

            logger.info(
                f"Final output committed: "
                f"{output_path}"
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )

        logger.info(
            "WN TRANSLATOR RUN COMPLETED"
        )

        print()
        print("=" * 60)
        print("TRANSLATION COMPLETE")
        print("=" * 60)

        print(
            f"Output: {output_path}"
        )

    except KeyboardInterrupt:
        logger.warning(
            "WN TRANSLATOR INTERRUPTED"
        )

        print(
            "\nTranslation dihentikan oleh user."
        )

        raise SystemExit(130)

    except Exception as exc:
        logger.exception(
            f"WN TRANSLATOR FAILED: {exc}"
        )

        print()
        print(
            f"ERROR: {exc}"
        )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
