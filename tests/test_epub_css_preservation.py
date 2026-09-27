import sys
from pathlib import Path
from zipfile import ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub


FIXTURE = PROJECT_ROOT / "test_structure_fixture.epub"
SOURCE = PROJECT_ROOT / "test_css_source.epub"
OUTPUT = PROJECT_ROOT / "test_css_output.epub"


def test_epub_css_preservation():
    with ZipFile(FIXTURE, "r") as original:
        with ZipFile(SOURCE, "w") as modified:

            for info in original.infolist():
                if info.filename == "OEBPS/chapter1.xhtml":
                    continue

                modified.writestr(
                    info,
                    original.read(info.filename),
                )

            modified.writestr(
                "OEBPS/styles/main.css",
                b"body { font-family: serif; }",
            )

            chapter1 = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<link rel="stylesheet" type="text/css"
      href="styles/main.css"/>
</head>
<body>
<h1>Chapter 1</h1>
<p>Alice enters.</p>
</body>
</html>
"""

            modified.writestr(
                "OEBPS/chapter1.xhtml",
                chapter1.encode("utf-8"),
            )

    document = parse_epub(SOURCE)

    styles = document.metadata["epub"]["spine_stylesheets"]

    assert styles["chapter1"]["links"] == [
        "styles/main.css"
    ]

    assert styles["chapter1"]["resolved_paths"] == [
        "OEBPS/styles/main.css"
    ]

    reconstruct_epub(
        document,
        OUTPUT,
        source_path=SOURCE,
    )

    with ZipFile(OUTPUT, "r") as rebuilt:
        assert "OEBPS/styles/main.css" in rebuilt.namelist()

        chapter1 = rebuilt.read(
            "OEBPS/chapter1.xhtml"
        ).decode("utf-8")

        assert (
            '<link rel="stylesheet" type="text/css" '
            'href="styles/main.css"/>'
        ) in chapter1

        assert (
            rebuilt.read("OEBPS/styles/main.css")
            == b"body { font-family: serif; }"
        )

    SOURCE.unlink(missing_ok=True)
    OUTPUT.unlink(missing_ok=True)


if __name__ == "__main__":
    test_epub_css_preservation()
    print("PASS: EPUB CSS preservation")
