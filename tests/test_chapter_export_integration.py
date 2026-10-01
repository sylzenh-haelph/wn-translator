from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from main import export_chapter
from parsers.epub_parser import parse_epub
from reconstruction.epub_validator import validate_epub
from translation.chapter_splitter import DocumentChapterSplitter


SOURCE = Path("/storage/emulated/0/Download/The_Silver_Gate_Test.epub")


def test_chapter_export_integration():
    assert SOURCE.is_file(), f"Source EPUB tidak ditemukan: {SOURCE}"

    source_before = SOURCE.read_bytes()

    document = parse_epub(SOURCE)
    chapters = DocumentChapterSplitter().split(document)

    assert chapters, "Tidak ada chapter yang berhasil di-split."

    chapter = chapters[0]

    original_title = chapter.title
    chapter.translated_title = f"{original_title} (Terjemahan)"

    with TemporaryDirectory() as tmp:
        output_dir = Path(tmp)

        export_chapter(
            input_path=SOURCE,
            source_document=document,
            chapter=chapter,
            index=1,
            output_dir=output_dir,
            suffix=".epub",
        )

        output_files = list(output_dir.glob("*.epub"))

        assert len(output_files) == 1, (
            f"Jumlah output chapter tidak sesuai: {output_files}"
        )

        output = output_files[0]

        assert output.is_file()
        assert output.stat().st_size > 0

        validation = validate_epub(output)
        assert validation is True or getattr(validation, "passed", False), (
            f"Chapter EPUB gagal divalidasi: {validation}"
        )

        with ZipFile(output) as zf:
            names = zf.namelist()

            xhtml_files = [
                name for name in names
                if name.lower().endswith((".xhtml", ".html"))
            ]

            assert xhtml_files, "Tidak ada XHTML/HTML pada chapter EPUB."

            combined = "\n".join(
                zf.read(name).decode("utf-8", errors="ignore")
                for name in xhtml_files
            )

            if chapter.translated_title not in combined:
                print("EXPECTED TITLE:", repr(chapter.translated_title))
                print("XHTML FILES:", xhtml_files)
                for name in xhtml_files:
                    content = zf.read(name).decode("utf-8", errors="ignore")
                    if "The Map" in content or "Chapter" in content:
                        print(f"--- {name} ---")
                        print(content[:12000])
                raise AssertionError(
                    "Bilingual chapter title tidak ditemukan pada XHTML hasil export."
                )

            assert chapter.paragraphs[0].text in combined

    source_after = SOURCE.read_bytes()
    assert source_before == source_after, "Source EPUB berubah setelah export."


if __name__ == "__main__":
    test_chapter_export_integration()
    print("CHAPTER EXPORT INTEGRATION TEST: PASS")
