import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub


SOURCE = PROJECT_ROOT / "test_metadata_roundtrip.epub"
OUTPUT = PROJECT_ROOT / "test_metadata_roundtrip_output.epub"


CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0"
xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf"
      media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

OPF = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
xmlns:dc="http://purl.org/dc/elements/1.1/"
version="3.0"
unique-identifier="book-id">

  <metadata>
    <dc:title>Roundtrip Novel</dc:title>
    <dc:creator id="creator">Roundtrip Author</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="book-id">urn:uuid:roundtrip-123</dc:identifier>
    <dc:publisher>Roundtrip Publisher</dc:publisher>
    <dc:description>Roundtrip description.</dc:description>
    <dc:date>2026-09-27</dc:date>
    <dc:subject>Fantasy</dc:subject>
    <meta property="dcterms:modified">2026-09-27T00:00:00Z</meta>
    <meta name="calibre:series" content="Roundtrip Series"/>
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

XHTML = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<h1>Chapter 1</h1>
<p>Roundtrip text.</p>
</body>
</html>
"""


def create_fixture():
    with ZipFile(
        SOURCE,
        "w",
        compression=ZIP_DEFLATED,
    ) as z:
        z.writestr(
            "META-INF/container.xml",
            CONTAINER,
        )
        z.writestr(
            "OEBPS/content.opf",
            OPF,
        )
        z.writestr(
            "OEBPS/chapter1.xhtml",
            XHTML,
        )


def get_metadata(document):
    metadata = document.metadata["epub"]["package_metadata"]

    dc = {
        item["name"]: item
        for item in metadata["dc"]
    }

    meta = metadata["meta"]

    return metadata, dc, meta


def test_metadata_roundtrip():
    create_fixture()

    original = parse_epub(SOURCE)

    reconstruct_epub(
        original,
        OUTPUT,
        source_path=SOURCE,
    )

    rebuilt = parse_epub(OUTPUT)

    original_metadata, original_dc, original_meta = (
        get_metadata(original)
    )

    rebuilt_metadata, rebuilt_dc, rebuilt_meta = (
        get_metadata(rebuilt)
    )

    assert original.title == rebuilt.title
    assert original.author == rebuilt.author

    assert (
        original_metadata["package_attributes"]
        == rebuilt_metadata["package_attributes"]
    )

    for field in [
        "title",
        "creator",
        "language",
        "identifier",
        "publisher",
        "description",
        "date",
        "subject",
    ]:
        assert field in original_dc
        assert field in rebuilt_dc

        assert (
            original_dc[field]["text"]
            == rebuilt_dc[field]["text"]
        )

        assert (
            original_dc[field]["attributes"]
            == rebuilt_dc[field]["attributes"]
        )

    original_meta_normalized = sorted(
        (
            item["text"],
            sorted(item["attributes"].items()),
        )
        for item in original_meta
    )

    rebuilt_meta_normalized = sorted(
        (
            item["text"],
            sorted(item["attributes"].items()),
        )
        for item in rebuilt_meta
    )

    assert (
        original_meta_normalized
        == rebuilt_meta_normalized
    )

    SOURCE.unlink(missing_ok=True)
    OUTPUT.unlink(missing_ok=True)


if __name__ == "__main__":
    test_metadata_roundtrip()
    print("PASS: EPUB metadata roundtrip")
