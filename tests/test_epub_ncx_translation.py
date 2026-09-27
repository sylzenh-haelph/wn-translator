import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "test_navigation_fixture.epub"
OUTPUT = ROOT / "test_epub_ncx_translation_output.epub"

NCX_NS = "http://www.daisy.org/z3986/2005/ncx"


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def main():
    assert SOURCE.exists(), f"Fixture tidak ditemukan: {SOURCE}"

    document = parse_epub(SOURCE)

    translations = {
        "p0000": "Bab 1",
        "p0001": "Alice memasuki istana.",
        "p0002": "Bab 2",
        "p0003": "Marcus mengikuti Alice.",
    }

    for paragraph in document.paragraphs:
        translated = translations[paragraph.id]

        if paragraph.runs:
            paragraph.runs[0].text = translated

    reconstruct_epub(
        document,
        OUTPUT,
        source_path=SOURCE,
    )

    assert OUTPUT.exists()

    with ZipFile(OUTPUT, "r") as archive:
        assert "OEBPS/toc.ncx" in archive.namelist()

        ncx = archive.read(
            "OEBPS/toc.ncx"
        ).decode("utf-8")

    root = ET.fromstring(ncx)

    assert local_name(root.tag) == "ncx"

    nav_map = None

    for element in root.iter():
        if local_name(element.tag) == "navMap":
            nav_map = element
            break

    assert nav_map is not None

    nav_points = [
        element
        for element in nav_map
        if local_name(element.tag) == "navPoint"
    ]

    assert len(nav_points) == 2

    expected = [
        ("chapter1", "Bab 1", "chapter1.xhtml"),
        ("chapter2", "Bab 2", "chapter2.xhtml"),
    ]

    for nav_point, (expected_id, expected_title, expected_src) in zip(
        nav_points,
        expected,
    ):
        assert nav_point.get("id") == expected_id

        label = None
        content = None

        for child in nav_point:
            name = local_name(child.tag)

            if name == "navLabel":
                label = child

            elif name == "content":
                content = child

        assert label is not None
        assert content is not None

        text_element = next(
            (
                child
                for child in label
                if local_name(child.tag) == "text"
            ),
            None,
        )

        assert text_element is not None
        assert text_element.text == expected_title
        assert content.get("src") == expected_src

    # Original English chapter labels must be gone.
    assert "Chapter 1" not in ncx
    assert "Chapter 2" not in ncx

    OUTPUT.unlink(missing_ok=True)

    print("PASS: EPUB NCX navigation translation")


if __name__ == "__main__":
    main()
