from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from parsers.epub_parser import parse_epub
from reconstruction.epub_validator import validate_epub


ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "main.py"


def create_fixture_epub(path: Path) -> None:
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0"
    xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile
      full-path="OEBPS/content.opf"
      media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

    content_opf = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
    version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">e2e-test-book</dc:identifier>
    <dc:title>E2E Test Novel</dc:title>
    <dc:creator>E2E Test Author</dc:creator>
    <dc:language>en</dc:language>
  </metadata>

  <manifest>
    <item id="chapter1"
          href="chapter1.xhtml"
          media-type="application/xhtml+xml"/>
  </manifest>

  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>
"""

    chapter_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <title>Chapter 1</title>
</head>
<body>
  <h1>Chapter 1: The Gate</h1>
  <p>Alice entered the Royal Palace.</p>
  <p>She carried the Silver Sword and waited at the gate.</p>
</body>
</html>
"""

    nav_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>Navigation</title>
</head>
<body>
  <nav epub:type="toc">
    <ol>
      <li>
        <a href="chapter1.xhtml">Chapter 1: The Gate</a>
      </li>
    </ol>
  </nav>
</body>
</html>
"""

    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        zf.writestr(
            "META-INF/container.xml",
            container_xml,
        )
        zf.writestr(
            "OEBPS/content.opf",
            content_opf,
        )
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            chapter_xhtml,
        )
        zf.writestr(
            "OEBPS/nav.xhtml",
            nav_xhtml,
        )


def run_e2e() -> None:
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY belum tersedia. "
            "Set environment variable tersebut sebelum menjalankan E2E."
        )

    with tempfile.TemporaryDirectory(
        prefix="wn-translator-e2e-"
    ) as temp:
        temp_dir = Path(temp)

        input_epub = temp_dir / "input.epub"
        output_epub = temp_dir / "output.epub"
        project_dir = temp_dir / "project"

        create_fixture_epub(input_epub)

        env = os.environ.copy()
        env["WN_RESEARCH_ENABLED"] = "true"
        env["WN_QA_ENABLED"] = "true"

        command = [
            sys.executable,
            str(MAIN),
            str(input_epub),
            "--output",
            str(output_epub),
            "--project-dir",
            str(project_dir),
            "--model",
            "gemini-3.5-flash-lite",
            "--max-retries",
            "1",
            "--timeout",
            "120",
            "--qa-max-retries",
            "2",
            "--max-chunk-tokens",
            "500",
        ]

        print("=== PRODUCTION E2E ===")
        print(f"Input   : {input_epub}")
        print(f"Output  : {output_epub}")
        print(f"Project : {project_dir}")
        print()
        print("Running main.py...")
        print()

        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
        )

        print("----- STDOUT -----")
        print(completed.stdout)

        if completed.stderr:
            print("----- STDERR -----")
            print(completed.stderr)

        if completed.returncode != 0:
            raise AssertionError(
                f"main.py gagal dengan exit code "
                f"{completed.returncode}"
            )

        if not output_epub.exists():
            raise AssertionError(
                "Output EPUB tidak dibuat."
            )

        if output_epub.stat().st_size <= 0:
            raise AssertionError(
                "Output EPUB berukuran 0 byte."
            )

        validation = validate_epub(output_epub)

        if not validation.passed:
            details = "\n".join(
                f"[{issue.severity}] "
                f"{issue.rule}: {issue.message}"
                for issue in validation.issues
            )
            raise AssertionError(
                "Output EPUB gagal validasi:\n" + details
            )

        output_document = parse_epub(output_epub)

        if output_document.title != "E2E Test Novel":
            raise AssertionError(
                f"Title berubah: {output_document.title!r}"
            )

        if output_document.author != "E2E Test Author":
            raise AssertionError(
                f"Author berubah: {output_document.author!r}"
            )

        output_text = [
            paragraph.text
            for paragraph in output_document.paragraphs
            if paragraph.text.strip()
        ]

        if not output_text:
            raise AssertionError(
                "Output tidak memiliki paragraph."
            )

        if len(output_text) < 3:
            raise AssertionError(
                "Struktur paragraph output tidak lengkap."
            )

        progress_dir = project_dir / "progress"
        cache_dir = project_dir / "cache"
        logs_dir = project_dir / "logs"

        if not progress_dir.exists():
            raise AssertionError(
                "Direktori progress tidak dibuat."
            )

        if not cache_dir.exists():
            raise AssertionError(
                "Direktori cache tidak dibuat."
            )

        if not logs_dir.exists():
            raise AssertionError(
                "Direktori logs tidak dibuat."
            )

        progress_files = list(
            progress_dir.rglob("*.json")
        )

        if not progress_files:
            raise AssertionError(
                "Tidak ditemukan progress JSON."
            )

        log_files = list(
            logs_dir.rglob("*")
        )

        if not log_files:
            raise AssertionError(
                "Tidak ditemukan file log."
            )

        print("----- E2E ASSERTIONS -----")
        print(f"Output size       : {output_epub.stat().st_size:,} bytes")
        print(f"Output paragraphs : {len(output_text)}")
        print(f"Progress files    : {len(progress_files)}")
        print(f"Log files         : {len(log_files)}")
        print("EPUB validation   : PASS")
        print("Production CLI    : PASS")
        print()
        print("PRODUCTION E2E: PASS")


if __name__ == "__main__":
    run_e2e()
