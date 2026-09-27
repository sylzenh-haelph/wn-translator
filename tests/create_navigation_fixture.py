from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "test_navigation_fixture.epub"


CONTAINER = """\
<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0"
 xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf"
      media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""

OPF = """\
<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0"
 xmlns="http://www.idpf.org/2007/opf"
 unique-identifier="bookid">

  <metadata
    xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Navigation Test</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">urn:test:navigation</dc:identifier>
  </metadata>

  <manifest>
    <item id="chapter1"
      href="chapter1.xhtml"
      media-type="application/xhtml+xml"/>

    <item id="chapter2"
      href="chapter2.xhtml"
      media-type="application/xhtml+xml"/>

    <item id="nav"
      href="nav.xhtml"
      media-type="application/xhtml+xml"
      properties="nav"/>
  </manifest>

  <spine toc="ncx">
    <itemref idref="chapter1"/>
    <itemref idref="chapter2"/>
  </spine>
</package>
"""

CHAPTER1 = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
<h1>Chapter 1</h1>
<p>Alice enters.</p>
</body>
</html>
"""

CHAPTER2 = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
<h1>Chapter 2</h1>
<p>Marcus follows.</p>
</body>
</html>
"""

NAV = """\
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Navigation</title></head>
<body>
<nav epub:type="toc" id="toc">
<ol>
<li><a href="chapter1.xhtml">Chapter 1</a></li>
<li><a href="chapter2.xhtml">Chapter 2</a></li>
</ol>
</nav>
</body>
</html>
"""

NCX = """\
<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx"
     version="2005-1">
<docTitle><text>Navigation Test</text></docTitle>
<navMap>
<navPoint id="chapter1">
<navLabel><text>Chapter 1</text></navLabel>
<content src="chapter1.xhtml"/>
</navPoint>
<navPoint id="chapter2">
<navLabel><text>Chapter 2</text></navLabel>
<content src="chapter2.xhtml"/>
</navPoint>
</navMap>
</ncx>
"""


def main():
    with ZipFile(
        OUTPUT,
        "w",
        compression=ZIP_DEFLATED,
    ) as zf:
        zf.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=0,
        )
        zf.writestr(
            "META-INF/container.xml",
            CONTAINER,
        )
        zf.writestr(
            "OEBPS/content.opf",
            OPF,
        )
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            CHAPTER1,
        )
        zf.writestr(
            "OEBPS/chapter2.xhtml",
            CHAPTER2,
        )
        zf.writestr(
            "OEBPS/nav.xhtml",
            NAV,
        )
        zf.writestr(
            "OEBPS/toc.ncx",
            NCX,
        )

    print(f"CREATED: {OUTPUT}")


if __name__ == "__main__":
    main()
