from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "test_epub_subheading_fixture.epub"


CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0"
    xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile
      full-path="OEBPS/content.opf"
      media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


OPF = """<?xml version="1.0" encoding="UTF-8"?>
<package
    xmlns="http://www.idpf.org/2007/opf"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    version="3.0"
    unique-identifier="bookid">

  <metadata>
    <dc:title>Subheading Test</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">urn:test:subheading</dc:identifier>
  </metadata>

  <manifest>
    <item
      id="chapter1"
      href="chapter1.xhtml"
      media-type="application/xhtml+xml"/>

    <item
      id="chapter2"
      href="chapter2.xhtml"
      media-type="application/xhtml+xml"/>
  </manifest>

  <spine>
    <itemref idref="chapter1"/>
    <itemref idref="chapter2"/>
  </spine>

</package>
"""


CHAPTER1 = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
<h1>Chapter 1</h1>
<p>Alice enters the palace.</p>
<h2>Scene: The Palace</h2>
<p>The guards look at her.</p>
<p>She continues walking.</p>
</body>
</html>
"""


CHAPTER2 = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
<h1>Chapter 2</h1>
<p>Marcus follows Alice.</p>
</body>
</html>
"""


def main():
    OUTPUT.unlink(missing_ok=True)

    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=0,
        )
        archive.writestr(
            "META-INF/container.xml",
            CONTAINER,
        )
        archive.writestr(
            "OEBPS/content.opf",
            OPF,
        )
        archive.writestr(
            "OEBPS/chapter1.xhtml",
            CHAPTER1,
        )
        archive.writestr(
            "OEBPS/chapter2.xhtml",
            CHAPTER2,
        )

    print(f"CREATED: {OUTPUT}")


if __name__ == "__main__":
    main()
