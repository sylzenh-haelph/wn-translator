import sys
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub
from models.document import Paragraph, TextRun


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "test_navigation_fixture.epub"
OUTPUT = ROOT / "test_epub_full_fidelity_output.epub"


def main():
    assert SOURCE.exists(), f"Fixture tidak ditemukan: {SOURCE}"

    # ============================================================
    # 1. Parse source EPUB
    # ============================================================

    source = parse_epub(SOURCE)
    structure = source.metadata["epub"]

    assert structure["opf_path"] == "OEBPS/content.opf"
    assert structure["spine"] == ["chapter1", "chapter2"]

    assert "navigation_items" in structure
    assert "xhtml_sources" in structure

    # ============================================================
    # 2. Buat document hasil terjemahan
    #
    #    Paragraph ID, style, dan jumlah paragraph tetap sama.
    # ============================================================

    translations = {
        "p0000": "Bab 1",
        "p0001": "Alice memasuki istana.",
        "p0002": "Bab 2",
        "p0003": "Marcus mengikutinya.",
    }

    translated_paragraphs = []

    for paragraph in source.paragraphs:
        translated = Paragraph(
            id=paragraph.id,
            runs=[
                TextRun(
                    text=translations[paragraph.id],
                    formatting=dict(
                        paragraph.runs[0].formatting
                    )
                    if paragraph.runs
                    else {},
                )
            ],
            style=dict(paragraph.style),
        )

        translated_paragraphs.append(translated)

    source.paragraphs = translated_paragraphs

    # ============================================================
    # 3. Rekonstruksi EPUB
    # ============================================================

    reconstruct_epub(
        source,
        OUTPUT,
        source_path=SOURCE,
    )

    assert OUTPUT.exists()
    assert OUTPUT.stat().st_size > 0

    # ============================================================
    # 4. Periksa struktur ZIP
    # ============================================================

    with ZipFile(OUTPUT, "r") as archive:
        names = archive.namelist()

        assert "mimetype" in names
        assert "META-INF/container.xml" in names
        assert "OEBPS/content.opf" in names

        assert "OEBPS/chapter1.xhtml" in names
        assert "OEBPS/chapter2.xhtml" in names
        assert "OEBPS/nav.xhtml" in names

        chapter1 = archive.read(
            "OEBPS/chapter1.xhtml"
        ).decode("utf-8")

        chapter2 = archive.read(
            "OEBPS/chapter2.xhtml"
        ).decode("utf-8")

        nav = archive.read(
            "OEBPS/nav.xhtml"
        ).decode("utf-8")

        opf = archive.read(
            "OEBPS/content.opf"
        ).decode("utf-8")

        # ========================================================
        # 5. Translation masuk ke chapter yang benar
        # ========================================================

        assert "Bab 1" in chapter1
        assert "Alice memasuki istana." in chapter1

        assert "Bab 2" in chapter2
        assert "Marcus mengikutinya." in chapter2

        # Source text tidak boleh tertinggal.
        assert "Chapter 1" not in chapter1
        assert "Alice enters." not in chapter1
        assert "Chapter 2" not in chapter2
        assert "Marcus follows." not in chapter2

        # ========================================================
        # 6. Navigation ikut diterjemahkan
        # ========================================================

        assert "Bab 1" in nav
        assert "Bab 2" in nav

        assert "Chapter 1" not in nav
        assert "Chapter 2" not in nav

        # ========================================================
        # 7. Manifest dan spine tetap benar
        # ========================================================

        assert 'id="chapter1"' in opf
        assert 'id="chapter2"' in opf

        assert '<itemref idref="chapter1"' in opf
        assert '<itemref idref="chapter2"' in opf

        # Navigation document tetap terdaftar.
        assert 'properties="nav"' in opf

        # ========================================================
        # 8. mimetype EPUB tetap valid
        # ========================================================

        assert names[0] == "mimetype"
        assert archive.read("mimetype") == b"application/epub+zip"

    # ============================================================
    # 9. Parse ulang hasil EPUB
    # ============================================================

    result = parse_epub(OUTPUT)

    assert len(result.paragraphs) == len(source.paragraphs)

    result_texts = [p.text for p in result.paragraphs]

    assert result_texts == [
        "Bab 1",
        "Alice memasuki istana.",
        "Bab 2",
        "Marcus mengikutinya.",
    ]

    # ============================================================
    # 10. Cleanup
    # ============================================================

    OUTPUT.unlink(missing_ok=True)

    print("PASS: EPUB full fidelity regression")


if __name__ == "__main__":
    main()
