from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from models.document import Document, Paragraph, TextRun
from reconstruction.epub_reconstructor import reconstruct_epub
from translation.chapter_reconstructor import ChapterReconstructor


def _heading(paragraph_id, text):
    return Paragraph(
        id=paragraph_id,
        runs=[
            TextRun(
                text=text,
                formatting={
                    "bold": True,
                },
            )
        ],
        style={
            "name": "Heading 1",
            "heading_level": 1,
        },
    )


def _paragraph(paragraph_id, text):
    return Paragraph(
        id=paragraph_id,
        runs=[TextRun(text=text)],
        style={},
    )


def _structure():
    return {
        "opf_path": "OEBPS/content.opf",
        "manifest": {
            "chap1": {
                "href": "chapter1.xhtml",
                "media_type": "application/xhtml+xml",
            },
            "chap2": {
                "href": "chapter2.xhtml",
                "media_type": "application/xhtml+xml",
            },
            "nav": {
                "href": "nav.xhtml",
                "media_type": "application/xhtml+xml",
                "properties": "nav",
            },
            "ncx": {
                "href": "toc.ncx",
                "media_type": "application/x-dtbncx+xml",
            },
        },
        "spine": [
            "chap1",
            "chap2",
        ],
        "spine_attributes": {
            "toc": "ncx",
        },
        "paragraph_spine_map": {
            "h1": "chap1",
            "p1": "chap1",
            "h2": "chap2",
            "p2": "chap2",
        },
        "navigation_items": {
            "nav": {
                "id": "nav",
            },
        },
        "xhtml_sources": {
            "nav": {
                "path": "OEBPS/nav.xhtml",
                "html": """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<nav epub:type="toc">
<ol>
<li><a href="chapter1.xhtml">Chapter 1: The Gate</a></li>
<li><a href="chapter2.xhtml">Chapter 2: The Royal Palace</a></li>
</ol>
</nav>
</body>
</html>
""",
            },
        },
        "navigation_path": "OEBPS/nav.xhtml",
        "ncx_path": "OEBPS/toc.ncx",
        "package_metadata": {},
    }


def _create_source_epub(path):
    nav = """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<body>
<nav epub:type="toc">
<ol>
<li><a href="chapter1.xhtml">Chapter 1: The Gate</a></li>
<li><a href="chapter2.xhtml">Chapter 2: The Royal Palace</a></li>
</ol>
</nav>
</body>
</html>
"""

    ncx = """<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
<head/>
<docTitle><text>Test Novel</text></docTitle>
<navMap>
<navPoint id="navPoint-1" playOrder="1">
<navLabel><text>Chapter 1: The Gate</text></navLabel>
<content src="chapter1.xhtml"/>
</navPoint>
<navPoint id="navPoint-2" playOrder="2">
<navLabel><text>Chapter 2: The Royal Palace</text></navLabel>
<content src="chapter2.xhtml"/>
</navPoint>
</navMap>
</ncx>
"""

    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns:dc="http://purl.org/dc/elements/1.1/"
         version="3.0"
         unique-identifier="bookid">
<metadata>
<dc:title>Test Novel</dc:title>
<dc:creator>Test Author</dc:creator>
<dc:identifier id="bookid">urn:uuid:test</dc:identifier>
</metadata>
<manifest>
<item id="chap1" href="chapter1.xhtml"
      media-type="application/xhtml+xml"/>
<item id="chap2" href="chapter2.xhtml"
      media-type="application/xhtml+xml"/>
<item id="nav" href="nav.xhtml"
      media-type="application/xhtml+xml"
      properties="nav"/>
<item id="ncx" href="toc.ncx"
      media-type="application/x-dtbncx+xml"/>
</manifest>
<spine toc="ncx">
<itemref idref="chap1"/>
<itemref idref="chap2"/>
</spine>
</package>
"""

    container = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0"
 xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles>
<rootfile full-path="OEBPS/content.opf"
 media-type="application/oebps-package+xml"/>
</rootfiles>
</container>
"""

    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
        )
        archive.writestr(
            "META-INF/container.xml",
            container,
        )
        archive.writestr(
            "OEBPS/content.opf",
            opf,
        )
        archive.writestr(
            "OEBPS/chapter1.xhtml",
            "<html><body><h1>Chapter 1: The Gate</h1></body></html>",
        )
        archive.writestr(
            "OEBPS/chapter2.xhtml",
            "<html><body><h1>Chapter 2: The Royal Palace</h1></body></html>",
        )
        archive.writestr(
            "OEBPS/nav.xhtml",
            nav,
        )
        archive.writestr(
            "OEBPS/toc.ncx",
            ncx,
        )


def test_bilingual_title_is_shared_by_heading_toc_and_ncx(tmp_path):
    bilingual_title_1 = (
        "Chapter 1: The Gate (Gerbang)"
    )
    bilingual_title_2 = (
        "Chapter 2: The Royal Palace (Istana Kerajaan)"
    )

    source_heading_1 = _heading(
        "h1",
        "Chapter 1: The Gate",
    )
    source_heading_2 = _heading(
        "h2",
        "Chapter 2: The Royal Palace",
    )

    reconstructor = ChapterReconstructor()

    chapter_1 = reconstructor.reconstruct(
        chapter_id="chapter_001",
        title=bilingual_title_1,
        source_paragraphs=[
            _paragraph(
                "p1",
                "Alice enters the gate.",
            )
        ],
        translated_paragraphs=[
            "Alice memasuki gerbang.",
        ],
        heading=source_heading_1,
    )

    chapter_2 = reconstructor.reconstruct(
        chapter_id="chapter_002",
        title=bilingual_title_2,
        source_paragraphs=[
            _paragraph(
                "p2",
                "Alice enters the royal palace.",
            )
        ],
        translated_paragraphs=[
            "Alice memasuki Istana Kerajaan.",
        ],
        heading=source_heading_2,
    )

    assert (
        chapter_1.heading.text
        == bilingual_title_1
    )
    assert (
        chapter_2.heading.text
        == bilingual_title_2
    )

    structure = _structure()

    document = Document(
        title="Test Novel",
        author="Test Author",
        paragraphs=[
            chapter_1.heading,
            *chapter_1.paragraphs,
            chapter_2.heading,
            *chapter_2.paragraphs,
        ],
        metadata={
            "epub": structure,
        },
    )

    source_path = (
        Path(tmp_path)
        / "source.epub"
    )
    output_path = (
        Path(tmp_path)
        / "bilingual_titles.epub"
    )

    _create_source_epub(source_path)

    reconstruct_epub(
        document=document,
        output_path=output_path,
        source_path=source_path,
    )

    assert output_path.exists()

    with ZipFile(output_path) as epub:
        chapter_1_xhtml = epub.read(
            "OEBPS/chapter1.xhtml"
        ).decode("utf-8")

        chapter_2_xhtml = epub.read(
            "OEBPS/chapter2.xhtml"
        ).decode("utf-8")

        nav_xhtml = epub.read(
            "OEBPS/nav.xhtml"
        ).decode("utf-8")

        ncx_xml = epub.read(
            "OEBPS/toc.ncx"
        ).decode("utf-8")

    assert bilingual_title_1 in chapter_1_xhtml
    assert bilingual_title_2 in chapter_2_xhtml

    assert bilingual_title_1 in nav_xhtml
    assert bilingual_title_2 in nav_xhtml

    assert bilingual_title_1 in ncx_xml
    assert bilingual_title_2 in ncx_xml

    assert "Chapter 1: The Gate</a>" not in nav_xhtml
    assert "Chapter 2: The Royal Palace</a>" not in nav_xhtml


def test_single_chapter_without_toc_keeps_bilingual_heading(tmp_path):
    bilingual_title = (
        "Chapter 1: The Gate (Gerbang)"
    )

    source_heading = _heading(
        "h1",
        "Chapter 1: The Gate",
    )

    reconstructor = ChapterReconstructor()

    chapter = reconstructor.reconstruct(
        chapter_id="chapter_001",
        title=bilingual_title,
        source_paragraphs=[],
        translated_paragraphs=[],
        heading=source_heading,
    )

    assert chapter.heading is not None
    assert (
        chapter.heading.text
        == bilingual_title
    )
    assert (
        chapter.heading.style["heading_level"]
        == 1
    )
    assert (
        chapter.heading.runs[0].formatting["bold"]
        is True
    )
