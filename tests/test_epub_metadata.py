import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from parsers.epub_parser import parse_epub


EPUB = PROJECT_ROOT / "test_metadata.epub"


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
    <dc:title>Metadata Test Novel</dc:title>
    <dc:creator id="creator">Test Author</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="book-id">urn:uuid:test-123</dc:identifier>
    <dc:publisher>Test Publisher</dc:publisher>
    <dc:description>A metadata test.</dc:description>
    <dc:date>2026-09-27</dc:date>
    <dc:subject>Fantasy</dc:subject>

    <meta property="dcterms:modified">
      2026-09-27T00:00:00Z
    </meta>

    <meta name="calibre:series" content="Test Series"/>
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
<p>Test paragraph.</p>
</body>
</html>
"""


def create_fixture():
    with ZipFile(
        EPUB,
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


def test_epub_metadata():
    create_fixture()

    document = parse_epub(EPUB)
    metadata = document.metadata["epub"][
        "package_metadata"
    ]

    assert document.title == "Metadata Test Novel"
    assert document.author == "Test Author"

    assert metadata["package_attributes"][
        "unique-identifier"
    ] == "book-id"

    dc = metadata["dc"]

    assert any(
        item["name"] == "language"
        and item["text"] == "en"
        for item in dc
    )

    assert any(
        item["name"] == "identifier"
        and item["text"] == "urn:uuid:test-123"
        and item["attributes"].get("id")
        == "book-id"
        for item in dc
    )

    assert any(
        item["name"] == "publisher"
        and item["text"] == "Test Publisher"
        for item in dc
    )

    assert any(
        item["name"] == "description"
        and item["text"] == "A metadata test."
        for item in dc
    )

    assert any(
        item["name"] == "date"
        and item["text"] == "2026-09-27"
        for item in dc
    )

    assert any(
        item["name"] == "subject"
        and item["text"] == "Fantasy"
        for item in dc
    )

    meta = metadata["meta"]

    assert any(
        item["attributes"].get("property")
        == "dcterms:modified"
        for item in meta
    )

    assert any(
        item["attributes"].get("name")
        == "calibre:series"
        and item["attributes"].get("content")
        == "Test Series"
        for item in meta
    )

    EPUB.unlink(missing_ok=True)


if __name__ == "__main__":
    test_epub_metadata()
    print("PASS: EPUB metadata parsing")
