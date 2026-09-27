from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

OUTPUT = Path("test_structure_fixture.epub")

with ZipFile(OUTPUT, "w") as epub:
    epub.writestr(
        "mimetype",
        "application/epub+zip",
        compress_type=0,
    )

    epub.writestr(
        "META-INF/container.xml",
        """<?xml version="1.0" encoding="utf-8"?>
<container version="1.0"
xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="OEBPS/content.opf"
media-type="application/oebps-package+xml"/>
</rootfiles>
</container>""",
    )

    epub.writestr(
        "OEBPS/content.opf",
        """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
version="3.0" unique-identifier="book-id">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="book-id">test</dc:identifier>
<dc:title>Structure Test</dc:title>
<dc:creator>Test Author</dc:creator>
<dc:language>en</dc:language>
</metadata>
<manifest>
<item id="chapter1"
href="chapter1.xhtml"
media-type="application/xhtml+xml"/>
<item id="chapter2"
href="chapter2.xhtml"
media-type="application/xhtml+xml"/>
</manifest>
<spine>
<itemref idref="chapter1"/>
<itemref idref="chapter2"/>
</spine>
</package>""",
    )

    epub.writestr(
        "OEBPS/chapter1.xhtml",
        """<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<h1>Chapter 1</h1>
<p>Alice enters.</p>
</body>
</html>""",
    )

    epub.writestr(
        "OEBPS/chapter2.xhtml",
        """<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<h1>Chapter 2</h1>
<p>Marcus follows.</p>
</body>
</html>""",
    )

print(OUTPUT)
