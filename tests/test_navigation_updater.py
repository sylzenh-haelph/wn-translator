from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parsers.epub_parser import parse_epub
from reconstruction.navigation_updater import (
    update_navigation,
)


FIXTURE = ROOT / "test_navigation_fixture.epub"


def main():
    document = parse_epub(FIXTURE)

    source_html = document.metadata[
        "epub"
    ]["xhtml_sources"].get("nav")

    # nav.xhtml bukan bagian spine, jadi parser
    # belum memasukkannya ke xhtml_sources.
    # Untuk unit test kita baca langsung dari fixture.
    if source_html is None:
        from zipfile import ZipFile

        with ZipFile(FIXTURE, "r") as zf:
            source_html = zf.read(
                "OEBPS/nav.xhtml"
            ).decode(
                "utf-8",
                errors="replace",
            )

    result = update_navigation(
        source_html,
        {
            "chapter1.xhtml": "Bab 1",
            "chapter2.xhtml": "Bab 2",
        },
    )

    assert "Bab 1" in result
    assert "Bab 2" in result

    assert "Chapter 1</a>" not in result
    assert "Chapter 2</a>" not in result

    # href tetap.
    assert 'href="chapter1.xhtml"' in result
    assert 'href="chapter2.xhtml"' in result

    # Struktur navigation tetap.
    assert "<nav" in result
    assert "<ol>" in result
    assert "<li>" in result

    print(
        "PASS: navigation label update"
    )


if __name__ == "__main__":
    main()
