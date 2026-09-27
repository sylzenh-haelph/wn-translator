import sys
from pathlib import Path
from zipfile import ZipFile

# Tambahkan root project ke Python path.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub


BASE = Path(__file__).resolve().parent
FIXTURE = PROJECT_ROOT / "test_structure_fixture.epub"
OUTPUT = BASE / "test_resource_preserved.epub"
RESOURCE_SOURCE = BASE / "test_resource_source.epub"


def test_epub_resource_preservation():
    # Buat EPUB sementara yang memiliki resource tambahan.
    with ZipFile(FIXTURE, "r") as original, ZipFile(
        RESOURCE_SOURCE, "w"
    ) as modified:
        for info in original.infolist():
            modified.writestr(info, original.read(info.filename))

        modified.writestr(
            "OEBPS/styles/main.css",
            b"body { font-family: serif; }",
        )

        modified.writestr(
            "OEBPS/images/cover.jpg",
            b"FAKE-JPEG-DATA",
        )

        modified.writestr(
            "OEBPS/fonts/test-font.ttf",
            b"FAKE-FONT-DATA",
        )

    source = parse_epub(RESOURCE_SOURCE)
    structure = source.metadata["epub"]

    reconstruct_epub(
        source,
        OUTPUT,
        source_path=RESOURCE_SOURCE,
    )

    assert OUTPUT.exists()

    with ZipFile(RESOURCE_SOURCE, "r") as original, ZipFile(
        OUTPUT, "r"
    ) as rebuilt:
        rebuilt_names = set(rebuilt.namelist())

        # Resource harus tetap ada.
        assert "OEBPS/styles/main.css" in rebuilt_names
        assert "OEBPS/images/cover.jpg" in rebuilt_names
        assert "OEBPS/fonts/test-font.ttf" in rebuilt_names

        # Isi resource harus identik.
        assert (
            rebuilt.read("OEBPS/styles/main.css")
            == original.read("OEBPS/styles/main.css")
        )

        assert (
            rebuilt.read("OEBPS/images/cover.jpg")
            == original.read("OEBPS/images/cover.jpg")
        )

        assert (
            rebuilt.read("OEBPS/fonts/test-font.ttf")
            == original.read("OEBPS/fonts/test-font.ttf")
        )

        # Struktur EPUB tetap ada.
        assert "mimetype" in rebuilt_names
        assert "META-INF/container.xml" in rebuilt_names
        assert structure["opf_path"] in rebuilt_names

        # XHTML harus direkonstruksi.
        chapter1 = rebuilt.read(
            "OEBPS/chapter1.xhtml"
        ).decode("utf-8")

        assert "Alice enters." in chapter1

    # Bersihkan file sementara.
    OUTPUT.unlink(missing_ok=True)
    RESOURCE_SOURCE.unlink(missing_ok=True)


if __name__ == "__main__":
    test_epub_resource_preservation()
    print("PASS: EPUB resource preservation")
