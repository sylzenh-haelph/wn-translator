from pathlib import Path
from zipfile import ZipFile
import sys

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parsers.epub_parser import parse_epub


FIXTURE = ROOT / "test_structure_fixture.epub"


def main():
    document = parse_epub(FIXTURE)

    epub = document.metadata["epub"]

    assert "xhtml_sources" in epub

    sources = epub["xhtml_sources"]

    assert "chapter1" in sources
    assert "chapter2" in sources

    for idref in ("chapter1", "chapter2"):
        entry = sources[idref]

        assert "path" in entry
        assert "html" in entry

        assert entry["path"].endswith(
            f"{idref}.xhtml"
        )

        assert "<html" in entry["html"].lower()
        assert "<body" in entry["html"].lower()

    with ZipFile(FIXTURE, "r") as zf:
        original_chapter1 = zf.read(
            "OEBPS/chapter1.xhtml"
        ).decode(
            "utf-8",
            errors="replace",
        )

        original_chapter2 = zf.read(
            "OEBPS/chapter2.xhtml"
        ).decode(
            "utf-8",
            errors="replace",
        )

    assert sources["chapter1"]["html"] == original_chapter1
    assert sources["chapter2"]["html"] == original_chapter2

    print("PASS: EPUB XHTML source preservation")


if __name__ == "__main__":
    main()
