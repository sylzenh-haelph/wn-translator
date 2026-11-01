from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zipfile import ZIP_STORED, ZipFile

from models.document import Document, Paragraph, TextRun
from reconstruction.epub_reconstructor import reconstruct_epub

OPF = (
    '<?xml version="1.0"?>'
    '<package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
    '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>T</dc:title></metadata>'
    '<manifest>'
    '<item id="ch1" href="Text/ch1.xhtml" media-type="application/xhtml+xml"/>'
    '<item id="used" href="Images/used.jpg" media-type="image/jpeg"/>'
    '<item id="unused" href="Images/unused.jpg" media-type="image/jpeg"/>'
    '</manifest>'
    '<spine><itemref idref="ch1"/></spine></package>'
)

XHTML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>T</title></head>'
    '<body><p><img src="../Images/used.jpg" alt=""/>Hai</p></body></html>'
)


def make_source(path):
    with ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip", compress_type=ZIP_STORED)
        z.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
            '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
            "</rootfiles></container>",
        )
        z.writestr("OEBPS/content.opf", OPF)
        z.writestr("OEBPS/Text/ch1.xhtml", XHTML)
        z.writestr("OEBPS/Images/used.jpg", b"used")
        z.writestr("OEBPS/Images/unused.jpg", b"unused")


def test_chapter_only_keeps_referenced_media_only(tmp_path):
    source = tmp_path / "source.epub"
    make_source(source)
    out = tmp_path / "chapter.epub"

    structure = {
        "opf_path": "OEBPS/content.opf",
        "manifest": {
            "ch1": {"href": "Text/ch1.xhtml", "media_type": "application/xhtml+xml", "properties": ""},
            "used": {"href": "Images/used.jpg", "media_type": "image/jpeg", "properties": ""},
            "unused": {"href": "Images/unused.jpg", "media_type": "image/jpeg", "properties": ""},
        },
        "spine": ["ch1"],
        "paragraph_spine_map": {"p1": "ch1"},
        "spine_stylesheets": {},
        "xhtml_sources": {"ch1": {"path": "OEBPS/Text/ch1.xhtml", "html": XHTML}},
        "navigation_items": {},
        "package_metadata": {},
    }
    document = Document(
        title="T",
        author="",
        paragraphs=[Paragraph(id="p1", runs=[TextRun("Hai")], style={})],
        metadata={"epub": structure},
    )

    reconstruct_epub(document, out, source_path=source, chapter_only=True)

    with ZipFile(out) as z:
        names = set(z.namelist())
        opf = z.read("OEBPS/content.opf").decode("utf-8")

    assert "OEBPS/Images/used.jpg" in names
    assert "OEBPS/Images/unused.jpg" not in names
    assert "used.jpg" in opf
    assert "unused.jpg" not in opf
