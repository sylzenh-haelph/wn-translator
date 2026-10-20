from pathlib import Path
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Document, Paragraph, TextRun
from reconstruction.epub_reconstructor import reconstruct_epub
from reconstruction.epub_validator import validate_epub


def test_source_without_nav_gets_generated_nav(tmp_path):
    source = tmp_path / "source.epub"
    with ZipFile(source, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("OEBPS/Text/ch1.xhtml", '<html><body><p>x</p></body></html>')
    structure = {
        "opf_path": "OEBPS/content.opf",
        "manifest": {"ch1": {"href": "Text/ch1.xhtml", "media_type": "application/xhtml+xml", "properties": ""}},
        "spine": ["ch1"],
        "paragraph_spine_map": {"p1": "ch1"},
        "spine_attributes": {},
        "spine_stylesheets": {},
        "xhtml_sources": {},
        "navigation_items": {},
        "package_metadata": {},
    }
    document = Document(
        title="T",
        author="A",
        paragraphs=[Paragraph(id="p1", runs=[TextRun(text="Isi")])],
        metadata={"epub": structure},
    )
    out = tmp_path / "out.epub"
    reconstruct_epub(document, out, source_path=source)

    with ZipFile(out) as z:
        opf = z.read("OEBPS/content.opf").decode("utf-8")
        nav = z.read("OEBPS/nav-generated.xhtml").decode("utf-8")
    assert 'properties="nav"' in opf
    assert 'href="Text/ch1.xhtml"' in nav
    assert "NAV_EXISTS" not in [issue.rule for issue in validate_epub(out).issues]
