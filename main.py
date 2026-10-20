from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from config.settings import load_config
from parsers.docx_parser import parse_docx
from parsers.epub_parser import parse_epub
from reconstruction.docx_reconstructor import reconstruct_docx
from reconstruction.epub_reconstructor import reconstruct_epub
from reconstruction.epub_validator import validate_epub
from research.runtime import build_research_service
from storage.logger import ProjectLogger
from storage.progress_db import ProgressDB
from storage.translation_stats import TranslationStats
from translation.chapter_reconstructor import ChapterReconstructor
from models.document import Document, TextRun
from translation.chapter_splitter import DocumentChapterSplitter
from translation.chapter_title_translator import ChapterTitleTranslator
from translation.ai_spine_classifier import classify_spine_document_with_ai
from translation.chapter_translation_assembler import ChapterTranslationAssembler
from translation.chunker import build_chunks
from translation.document_assembler import DocumentAssembler
from translation.glossary import apply_glossary, load_glossary, merge_scan_glossary
from translation.runtime import build_chapter_processor, build_failover_client


SUPPORTED_INPUTS = {".epub", ".docx"}
SUPPORTED_OUTPUTS = {".epub", ".docx"}


def make_failover_logger(logger, role):
    def notify(label, exc):
        message = (
            f"{role} gagal di {label}, pindah ke cadangan. "
            f"Penyebab: {exc}"
        )
        print(f"  WARNING: {message}")
        logger.warning(message)

    return notify


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


def backup_existing_output(
    output_path: Path,
    retention: int = 5,
    logger: ProjectLogger | None = None,
):
    if not output_path.exists():
        return None

    if not output_path.is_file():
        raise RuntimeError(
            f"Output lama bukan file: {output_path}"
        )

    backup_dir = output_path.parent / ".wn-translator-backups"
    backup_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = time.strftime(
        "%Y%m%d-%H%M%S"
    )
    timestamp_ns = time.time_ns() % 1_000_000_000

    backup_path = (
        backup_dir
        / (
            f"{output_path.stem}.{timestamp}-"
            f"{timestamp_ns:09d}{output_path.suffix}"
        )
    )

    counter = 1
    while backup_path.exists():
        backup_path = (
            backup_dir
            / f"{output_path.stem}.{timestamp}-{counter}"
            f"{output_path.suffix}"
        )
        counter += 1

    shutil.copy2(
        output_path,
        backup_path,
    )

    backups = sorted(
        (
            path
            for path in backup_dir.iterdir()
            if path.is_file()
            and path.name.startswith(
                f"{output_path.stem}."
            )
            and path.suffix == output_path.suffix
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    if retention == 0:
        for old_backup in backups:
            old_backup.unlink()
    elif len(backups) > retention:
        for old_backup in backups[retention:]:
            old_backup.unlink()

    message = (
        f"Backup output lama: {backup_path}"
    )

    print(f"  {message}")

    if logger:
        logger.info(message)

    return backup_path


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
            source_path=input_path if input_path.suffix.lower() == ".epub" else None,
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


def _safe_chapter_filename(chapter, index, suffix):
    # Nama pakai nomor saja: judul yang berubah tidak membuat file duplikat.
    return f"chapter-{index:02d}{suffix}"


def _build_chapter_document(
    source_document,
    chapter,
):
    from copy import deepcopy

    paragraphs = []

    if chapter.heading is not None:
        heading = deepcopy(chapter.heading)

        translated_title = (
            getattr(chapter, "translated_title", None)
            or chapter.title
        )

        if heading.runs:
            heading.runs[0].text = translated_title
            for run in heading.runs[1:]:
                run.text = ""
        else:
            heading.runs.append(
                TextRun(
                    text=translated_title,
                    formatting={},
                )
            )

        paragraphs.append(heading)

    paragraphs.extend(chapter.paragraphs)

    metadata = {}

    if source_document.metadata:
        metadata = source_document.metadata.copy()

    epub = metadata.get("epub")

    if epub:
        from copy import deepcopy

        structure = deepcopy(epub)

        paragraph_ids = {
            paragraph.id
            for paragraph in paragraphs
        }

        paragraph_map = structure.get(
            "paragraph_spine_map",
            {},
        )

        idrefs = []
        for paragraph_id in paragraph_ids:
            idref = paragraph_map.get(paragraph_id)
            if idref and idref not in idrefs:
                idrefs.append(idref)

        if idrefs:
            structure["spine"] = [
                idref
                for idref in structure.get("spine", [])
                if idref in idrefs
            ]

            structure["paragraph_spine_map"] = {
                paragraph_id: idref
                for paragraph_id, idref in paragraph_map.items()
                if paragraph_id in paragraph_ids
            }

            structure["xhtml_sources"] = {
                idref: source
                for idref, source in structure.get(
                    "xhtml_sources",
                    {},
                ).items()
                if idref in idrefs
            }

            structure["spine_stylesheets"] = {
                idref: styles
                for idref, styles in structure.get(
                    "spine_stylesheets",
                    {},
                ).items()
                if idref in idrefs
            }

            manifest = structure.get("manifest", {})
            structure["manifest"] = {
                manifest_id: item
                for manifest_id, item in manifest.items()
                if (
                    manifest_id in idrefs
                    or str(item.get("media_type", "")).lower()
                    not in {
                        "application/xhtml+xml",
                        "application/x-dtbncx+xml",
                    }
                )
            }

            # Chapter export berdiri sendiri, jadi jangan
            # membawa TOC/NCX novel penuh.
            structure.pop("navigation_items", None)

            spine_attributes = dict(
                structure.get("spine_attributes", {})
            )
            spine_attributes.pop("toc", None)
            structure["spine_attributes"] = spine_attributes

        metadata["epub"] = structure

    return Document(
        title=source_document.title,
        author=source_document.author,
        paragraphs=paragraphs,
        metadata=metadata,
    )


def _prune_chapter_epub(
    epub_path: Path,
    chapter_document,
):
    import posixpath
    import re
    from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

    structure = chapter_document.metadata.get("epub", {})
    sources = structure.get("xhtml_sources", {})
    spine = structure.get("spine", [])

    keep_xhtml = set()

    for idref in spine:
        source = sources.get(idref)

        if isinstance(source, dict):
            path = source.get("path")
        else:
            path = source

        if path:
            keep_xhtml.add(str(path).lstrip("/"))

    # Dokumen navigasi bukan bagian spine, tapi wajib ada agar manifest valid.
    # Dibaca dari OPF hasil build, karena nav buatan dibuat setelah daftar ini.
    with ZipFile(epub_path, "r") as source_zip:
        container = source_zip.read("META-INF/container.xml").decode("utf-8")
        opf_name = re.search(r'full-path="([^"]+)"', container).group(1)
        opf = source_zip.read(opf_name).decode("utf-8")

    for item in re.findall(r"<item\b[^>]*>", opf):
        if re.search(r'properties="[^"]*\bnav\b', item):
            href = re.search(r'href="([^"]+)"', item).group(1)
            keep_xhtml.add(posixpath.normpath(posixpath.join(posixpath.dirname(opf_name), href)))

    if not keep_xhtml:
        raise RuntimeError(
            "Tidak dapat menentukan XHTML chapter yang harus dipertahankan."
        )

    temp_path = epub_path.with_suffix(".chapter-pruned.epub")

    try:
        with ZipFile(epub_path, "r") as source_zip:
            infos = source_zip.infolist()

            with ZipFile(
                temp_path,
                "w",
                compression=ZIP_DEFLATED,
            ) as output_zip:
                for info in infos:
                    name = info.filename
                    normalized = name.lstrip("/")

                    if normalized.lower().endswith(
                        (".xhtml", ".html", ".htm")
                    ):
                        if normalized not in keep_xhtml:
                            continue

                    if normalized.lower().endswith(".ncx"):
                        continue

                    data = source_zip.read(name)

                    if normalized == "mimetype":
                        output_zip.writestr(
                            info,
                            data,
                            compress_type=ZIP_STORED,
                        )
                    else:
                        output_zip.writestr(
                            info,
                            data,
                        )

        temp_path.replace(epub_path)

    finally:
        if temp_path.exists():
            temp_path.unlink()


def _slim_chapter_epub(epub_path: Path, title: str):
    # Buang media yang tidak dirujuk chapter ini, dan pastikan ada daftar isi EPUB 3.
    import posixpath
    import re
    from xml.sax.saxutils import escape
    from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

    with ZipFile(epub_path, "r") as zin:
        infos = zin.infolist()
        data = {info.filename: zin.read(info.filename) for info in infos}

    container = data["META-INF/container.xml"].decode("utf-8")
    opf_path = re.search(r'full-path="([^"]+)"', container).group(1)
    base = posixpath.dirname(opf_path)
    opf = data[opf_path].decode("utf-8")

    text = "\n".join(
        content.decode("utf-8", "ignore")
        for name, content in data.items()
        if name.lower().endswith((".xhtml", ".html", ".htm", ".css"))
    )

    # shortcut: cocokkan nama file saja, aset dengan nama sama di tempat lain ikut tersimpan
    for name in list(data):
        if name == "mimetype" or name.startswith("META-INF/"):
            continue
        if name.lower().endswith((".xhtml", ".html", ".htm", ".css", ".opf", ".ncx", ".xml")):
            continue
        if posixpath.basename(name) in text:
            continue
        del data[name]
        href = posixpath.relpath(name, base or ".")
        opf = re.sub(r'<item\b[^>]*href="' + re.escape(href) + r'"[^>]*/>\s*', "", opf)
        opf = re.sub(r'<meta\s+name="cover"[^>]*/>\s*', "", opf)

    nav_name = posixpath.join(base, "chapter-nav.xhtml")
    if not re.search(r'properties="[^"]*\bnav\b', opf):
        idref = re.search(r'<itemref\b[^>]*idref="([^"]+)"', opf).group(1)
        item = next(i for i in re.findall(r"<item\b[^>]*>", opf) if f'id="{idref}"' in i)
        chapter_path = posixpath.normpath(
            posixpath.join(base, re.search(r'href="([^"]+)"', item).group(1))
        )
        link = posixpath.relpath(chapter_path, posixpath.dirname(nav_name) or ".")
        data[nav_name] = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">'
            "<head><title>Navigasi</title></head><body>"
            '<nav epub:type="toc" id="toc"><ol>'
            f'<li><a href="{escape(link)}">{escape(title)}</a></li>'
            "</ol></nav></body></html>"
        ).encode("utf-8")
        opf = opf.replace(
            "</manifest>",
            '<item id="chapter-nav" href="chapter-nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>',
            1,
        )

    data[opf_path] = opf.encode("utf-8")
    temp_path = epub_path.with_suffix(".slim.epub")
    names = [info.filename for info in infos if info.filename in data]
    names += [name for name in data if name not in names]

    try:
        with ZipFile(temp_path, "w") as zout:
            for name in names:
                if name == "mimetype":
                    zout.writestr(name, data[name], compress_type=ZIP_STORED)
                else:
                    zout.writestr(name, data[name], compress_type=ZIP_DEFLATED)
        temp_path.replace(epub_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def export_chapter(
    input_path: Path,
    source_document,
    chapter,
    index: int,
    output_dir: Path,
    suffix: str,
    logger: ProjectLogger | None = None,
):
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    filename = _safe_chapter_filename(
        chapter,
        index,
        suffix,
    )

    output_path = output_dir / filename
    temp_dir, temp_output = create_safe_output_path(
        output_path
    )

    try:
        chapter_document = _build_chapter_document(
            source_document,
            chapter,
        )

        reconstruct_output(
            input_path,
            chapter_document,
            temp_output,
        )

        if temp_output.suffix.lower() == ".epub":
            _prune_chapter_epub(
                temp_output,
                chapter_document,
            )
            _slim_chapter_epub(
                temp_output,
                getattr(chapter, "translated_title", None) or chapter.title,
            )

        validate_output(
            temp_output,
            logger=logger,
        )

        shutil.move(
            str(temp_output),
            str(output_path),
        )

        print(
            f"  Chapter export: {output_path}"
        )

        if logger:
            logger.info(
                f"Chapter export completed: "
                f"{chapter.chapter_id} | "
                f"{output_path}"
            )

    except Exception as exc:
        print(
            f"  WARNING: chapter export gagal: "
            f"{chapter.chapter_id} | {exc}"
        )

        if logger:
            logger.warning(
                f"Chapter export failed: "
                f"{chapter.chapter_id} | {exc}"
            )

    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )


def parse_chapter_list(value: str) -> set[int]:
    """Parse '3', '2-5', atau daftar '2,5,7-8' menjadi kumpulan nomor chapter."""
    numbers = set()
    for part in value.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            if not (start.strip().isdigit() and end.strip().isdigit()):
                raise ValueError("Format --chapter harus N, START-END, atau daftar dengan koma.")
            low, high = int(start), int(end)
            if low <= 0 or high < low:
                raise ValueError("Range chapter tidak valid.")
            numbers.update(range(low, high + 1))
        elif part.isdigit() and int(part) > 0:
            numbers.add(int(part))
        else:
            raise ValueError("Format --chapter harus N, START-END, atau daftar dengan koma.")
    return numbers


def parse_chapter_selection(value: str) -> tuple[int, int]:
    """Parse --chapter N or --chapter START-END into a 1-based range."""
    raw = value.strip()

    if not raw:
        raise ValueError("--chapter tidak boleh kosong.")

    if "-" in raw:
        parts = raw.split("-")

        if len(parts) != 2:
            raise ValueError(
                "Format --chapter harus N atau START-END."
            )

        start_raw, end_raw = (
            part.strip()
            for part in parts
        )

        if not start_raw.isdigit() or not end_raw.isdigit():
            raise ValueError(
                "Nomor chapter harus berupa bilangan bulat positif."
            )

        start = int(start_raw)
        end = int(end_raw)

        if start <= 0 or end <= 0:
            raise ValueError(
                "Nomor chapter harus lebih besar dari 0."
            )

        if start > end:
            raise ValueError(
                "Range chapter tidak valid: awal tidak boleh "
                "lebih besar dari akhir."
            )

        return start, end

    if not raw.isdigit():
        raise ValueError(
            "Format --chapter harus N atau START-END."
        )

    number = int(raw)

    if number <= 0:
        raise ValueError(
            "Nomor chapter harus lebih besar dari 0."
        )

    return number, number


def chapter_action(selected: bool, processor, chapter_id: str) -> str:
    """Chapter yang sudah selesai dipulihkan tanpa riset ulang."""
    status = processor.progress_db.load(chapter_id)["status"]
    if status == "completed":
        return "restore"
    return "translate" if selected else "skip"


def process_chapters(
    document,
    processor,
    config,
    logger: ProjectLogger | None = None,
    entity_service=None,
    export_chapters: bool = False,
    chapter_output_dir: Path | None = None,
    output_suffix: str = ".epub",
    input_path: Path | None = None,
    chapter_selection: tuple[int, int] | None = None,
    chapter_list_path: Path | None = None,
    glossary: list | None = None,
):
    ai_client = processor.translation_engine.client

    def ai_spine_classifier(
        paragraphs,
        document_id,
        source_document,
    ):
        return classify_spine_document_with_ai(
            client=ai_client,
            paragraphs=paragraphs,
            document_id=document_id,
            novel_title=source_document.title,
            author=source_document.author,
        )

    splitter = DocumentChapterSplitter()
    splitter.ai_classifier = ai_spine_classifier
    chapters = splitter.split(document)
    if chapter_list_path is not None:
        chapter_list_path.write_text(
            json.dumps([{"id": c.chapter_id, "title": c.title} for c in chapters], ensure_ascii=False),
            encoding="utf-8",
        )

    if chapter_selection is None:
        numbers = set(range(1, len(chapters) + 1))
    elif isinstance(chapter_selection, tuple):
        numbers = set(range(chapter_selection[0], chapter_selection[1] + 1))
    else:
        numbers = set(chapter_selection)

    if numbers and max(numbers) > len(chapters):
        raise ValueError(
            f"Chapter {max(numbers)} tidak tersedia. "
            f"Total chapter: {len(chapters)}."
        )

    selected_indexes = {number - 1 for number in numbers}

    assembler = ChapterTranslationAssembler()
    reconstructor = ChapterReconstructor()
    title_translator = ChapterTitleTranslator(processor.translation_engine.client)

    translated_chapters = []
    failed_ids = []
    stats = TranslationStats()
    translation_started = time.monotonic()

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
        action = chapter_action(
            (index - 1) in selected_indexes,
            processor,
            chapter.chapter_id,
        )
        if action == "skip":
            if logger:
                logger.info(
                    f"Chapter skipped by selection: "
                    f"{chapter.chapter_id} | "
                    f"{chapter.title}"
                )
            continue
        restore_only = action == "restore"

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

            reconstructed_chapter = reconstructor.reconstruct(
                chapter_id=chapter.chapter_id,
                title=bilingual_title,
                source_paragraphs=[],
                translated_paragraphs=[],
                heading=chapter.heading,
            )

            translated_chapters.append(
                reconstructed_chapter
            )

            stats.add_chapter(
                chapter_id=chapter.chapter_id,
                title=bilingual_title,
                paragraphs=len(chapter.paragraphs),
            )
            stats.mark_skipped_chapter()

            if (
                export_chapters
                and chapter_output_dir is not None
                and input_path is not None
            ):
                export_chapter(
                    input_path=input_path,
                    source_document=document,
                    chapter=reconstructed_chapter,
                    index=index,
                    output_dir=chapter_output_dir,
                    suffix=output_suffix,
                    logger=logger,
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

        if entity_service is not None and not restore_only:
            print("  Research  : analyzing entities...")

            if logger:
                logger.info(
                    f"Entity research started: "
                    f"{chapter.chapter_id}"
                )

            try:
                entity_result = entity_service.process_chapter(
                    chapter_id=chapter.chapter_id,
                    paragraphs=chapter.paragraphs,
                )

                resolved_entities = list(
                    entity_result.entities
                )
            except Exception as exc:
                resolved_entities = []
                print(
                    f"  WARNING: research gagal, lanjut tanpa entitas: {exc}"
                )
                if logger:
                    logger.warning(
                        f"Entity research failed, continuing without entities: "
                        f"{chapter.chapter_id} | {exc}"
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

        try:
            result = processor.process_chapter(
                chapter_id=chapter.chapter_id,
                chunks=chunks,
                chapter_context=chapter_context,
                initial_context_state=None,
                entity_resolutions=resolved_entities,
            )
        except Exception as exc:
            result = []
            failed_ids.append(chapter.chapter_id)
            print(
                f"  WARNING: terjemahan chapter gagal, chapter dibiarkan asli: {exc}"
            )
            if logger:
                logger.exception(
                    f"Chapter translation error: "
                    f"{chapter.chapter_id} | {exc}"
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

        chapter_passed = bool(result) and all(
            processed.qa_passed
            for processed in result
        )

        stats.add_chapter(
            chapter_id=chapter.chapter_id,
            title=bilingual_title,
            paragraphs=len(chapter.paragraphs),
            processed_chunks=result,
            entities=resolved_entities,
        )

        if not chapter_passed:
            print(
                "  QA        : FAILED - "
                "chapter dipertahankan dalam bentuk asli"
            )
            if logger:
                logger.warning(
                    f"Chapter translation failed QA: "
                    f"{chapter.chapter_id}"
                )
            continue

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

        translated_paragraphs = [
            apply_glossary(text, glossary or [])
            for text in translated_paragraphs
        ]
        bilingual_title = apply_glossary(bilingual_title, glossary or [])

        reconstructed_chapter = reconstructor.reconstruct(
            chapter_id=chapter.chapter_id,
            title=bilingual_title,
            source_paragraphs=chapter.paragraphs,
            translated_paragraphs=translated_paragraphs,
            heading=chapter.heading,
        )

        translated_chapters.append(
            reconstructed_chapter
        )

        stats.mark_completed_chapter()

        if (
            export_chapters
            and (index - 1) in selected_indexes
            and chapter_output_dir is not None
            and input_path is not None
        ):
            export_chapter(
                input_path=input_path,
                source_document=document,
                chapter=reconstructed_chapter,
                index=index,
                output_dir=chapter_output_dir,
                suffix=output_suffix,
                logger=logger,
            )

        if logger:
            logger.info(
                f"Chapter completed: "
                f"{chapter.chapter_id}"
            )

    stats.finish(time.monotonic() - translation_started)
    stats.failed_chapters = failed_ids

    # DocumentAssembler expects the complete chapter sequence.
    # Selected chapters use their translated reconstruction;
    # unselected chapters remain in their original source form.
    translated_by_index = {}

    for chapter in translated_chapters:
        for original_index, original_chapter in enumerate(
            chapters,
            start=1,
        ):
            if original_chapter.chapter_id == chapter.chapter_id:
                translated_by_index[original_index - 1] = chapter
                break

    complete_chapters = []

    for chapter_index, original_chapter in enumerate(chapters):
        translated_chapter = translated_by_index.get(
            chapter_index
        )

        if translated_chapter is not None:
            complete_chapters.append(translated_chapter)
        else:
            complete_chapters.append(original_chapter)

    return complete_chapters, stats


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
    list_path = project_dir / "chapters.json"
    if list_path.exists():
        chapters = [
            SimpleNamespace(chapter_id=item["id"], title=item["title"])
            for item in json.loads(list_path.read_text(encoding="utf-8"))
        ]
    else:
        # shortcut: sebelum run pertama, jumlah chapter bisa beda dari run (AI classifier); sama setelah run
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


def scan_glossary_file(input_path: Path, project_dir: Path, output: Path):

    config = load_config(project_dir=project_dir)
    if not config.research_enabled:
        raise SystemExit("Scan glosarium butuh riset aktif (WN_RESEARCH_ENABLED=1).")

    document = parse_document(input_path)
    research_client = build_failover_client(
        config,
        role="Research",
        primary_provider=config.research_provider,
        primary_model=config.research_model,
        fallbacks=config.research_fallbacks,
        max_retries=config.research_max_retries,
        timeout=config.research_timeout,
    )
    entity_service = build_research_service(
        project_dir=project_dir,
        client=research_client,
        document_title=document.title,
        author=document.author,
        research_timeout=config.research_timeout,
        research_max_retries=config.research_max_retries,
        max_attempts=config.research_max_attempts,
    )

    found = []
    # shortcut: semua bagian ikut diriset, termasuk halaman non-cerita; penyaringan menyusul
    for chapter in DocumentChapterSplitter().split(document):
        if not chapter.paragraphs:
            continue
        print(f"Riset: {chapter.chapter_id} | {chapter.title}")
        result = entity_service.process_chapter(
            chapter_id=chapter.chapter_id,
            paragraphs=chapter.paragraphs,
        )
        found.extend((entity.text, entity.entity_type) for entity in result.entities)

    added = merge_scan_glossary(found, output, document.title)
    print(f"Glosarium: {output} | entri baru: {added}")


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
        "--export-chapters",
        action="store_true",
        help="Export setiap chapter segera setelah selesai diterjemahkan",
    )

    parser.add_argument(
        "--chapter",
        default=None,
        help="Terjemahkan chapter tertentu: N, START-END, atau daftar dengan koma (2,4,6-8)",
    )

    parser.add_argument(
        "--chapter-output-dir",
        default=None,
        help="Direktori output chapter; default: <output>_chapters",
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
        "--scan-glossary",
        default=None,
        help="Scan entitas novel ini ke file glosarium baru (tanpa menerjemahkan)",
    )

    parser.add_argument(
        "--glossary",
        default="glossary/mt_v15.txt",
        help="File glosarium yang diterapkan otomatis ke hasil",
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

    if args.scan_glossary:
        scan_glossary_file(
            input_path,
            project_dir,
            Path(args.scan_glossary),
        )
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
            f"Config: translation={config.translation_provider!r}/"
            f"{config.translation_model!r} | "
            f"research={config.research_provider!r}/"
            f"{config.research_model!r} | "
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
            on_failover=make_failover_logger(logger, "Translasi"),
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

            # Research memakai client dengan cadangan (research_fallbacks).
            research_client = build_failover_client(
                config,
                role="Research",
                primary_provider=config.research_provider,
                primary_model=config.research_model,
                fallbacks=config.research_fallbacks,
                max_retries=config.research_max_retries,
                timeout=config.research_timeout,
                on_failover=make_failover_logger(logger, "Research"),
            )

            entity_service = build_research_service(
                project_dir=project_dir,
                client=research_client,
                document_title=document.title,
                author=document.author,
                research_timeout=config.research_timeout,
                research_max_retries=config.research_max_retries,
                max_attempts=config.research_max_attempts,
            )

            logger.info(
                "Entity research initialization completed"
            )

        chapter_output_dir = None

        if args.export_chapters:
            if args.chapter_output_dir is not None:
                chapter_output_dir = Path(
                    args.chapter_output_dir
                )
            else:
                chapter_output_dir = (
                    output_path.parent
                    / f"{output_path.stem}_chapters"
                )

            print(
                f"Chapter exports: {chapter_output_dir}"
            )

            logger.info(
                f"Chapter export enabled: "
                f"{chapter_output_dir}"
            )

        chapter_selection = None

        if args.chapter is not None:
            chapter_selection = parse_chapter_list(args.chapter)
            listed = ",".join(str(n) for n in sorted(chapter_selection))

            print(f"Chapter selection: {listed}")
            logger.info(f"Chapter selection: {listed}")

        for retry_round in range(1, 4):
            try:
                translated_chapters, translation_stats = process_chapters(
                    document,
                    processor,
                    config,
                    logger=logger,
                    entity_service=entity_service,
                    export_chapters=args.export_chapters,
                    chapter_output_dir=chapter_output_dir,
                    output_suffix=output_path.suffix.lower(),
                    input_path=input_path,
                    chapter_selection=chapter_selection,
                    chapter_list_path=project_dir / "chapters.json",
                    glossary=load_glossary(Path(args.glossary)),
                )
            except Exception as exc:
                if retry_round == 3:
                    raise
                print(f"\nERROR: {exc}. Diulang setelah 60 detik.")
                time.sleep(60)
                continue

            failed = translation_stats.failed_chapters
            if not failed or retry_round == 3:
                break
            print(
                f"\nChapter gagal: {', '.join(failed)}. "
                f"Diulang setelah 60 detik (putaran {retry_round + 1}/3)."
            )
            time.sleep(60)

        stats_path = project_dir / "stats" / "translation_stats.json"
        translation_stats.save(stats_path)

        summary = translation_stats.summary()

        print()
        print("TRANSLATION STATISTICS")
        print("-" * 60)
        print(
            f"Chapters       : {summary['completed_chapters']}/"
            f"{summary['chapters']}"
        )
        print(f"Paragraphs     : {summary['paragraphs']}")
        print(
            f"Chunks         : {summary['completed_chunks']}/"
            f"{summary['chunks']} completed"
        )
        print(f"Flagged chunks : {summary['flagged_chunks']}")
        print(
            f"QA             : {summary['qa_passed']} passed / "
            f"{summary['qa_failed']} failed"
        )
        print(f"Attempts       : {summary['attempts']}")
        print(f"Retries        : {summary['retries']}")
        print(
            f"Cache          : {summary['cache_hits']} hit / "
            f"{summary['cache_misses']} miss"
        )
        print(f"Entities       : {summary['entities']}")
        print(f"Research fail  : {summary['research_failed']}")
        print(f"Duration       : {summary['duration_seconds']:.2f}s")
        print(f"Stats file     : {stats_path}")

        if logger:
            logger.info(
                f"Translation statistics saved: {stats_path}"
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

            backup_existing_output(
                output_path,
                retention=config.backup_retention,
                logger=logger,
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
