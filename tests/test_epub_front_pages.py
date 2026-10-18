from pathlib import Path
import re
import sys
from zipfile import ZipFile

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from models.document import Document, Paragraph, TextRun
from reconstruction.epub_reconstructor import LINE_BREAK, _strip_chapter_prefix, reconstruct_epub


def _make_epub(tmp_path):
    cover = '<html><body><img src="../Images/cover.jpg"/></body></html>'
    source = tmp_path / "source.epub"
    with ZipFile(source, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("OEBPS/Text/cover.xhtml", cover)
        z.writestr("OEBPS/Images/cover.jpg", b"fakejpg")

    structure = {
        "opf_path": "OEBPS/content.opf",
        "manifest": {
            "cover": {"href": "Text/cover.xhtml", "media_type": "application/xhtml+xml", "properties": ""},
            "ch1": {"href": "Text/ch1.xhtml", "media_type": "application/xhtml+xml", "properties": ""},
        },
        "spine": ["cover", "ch1"],
        "paragraph_spine_map": {"p1": "ch1"},
        "spine_attributes": {},
        "spine_stylesheets": {},
        "xhtml_sources": {},
        "navigation_items": {},
        "package_metadata": {
            "dc": [
                {"name": "title", "text": "T", "attributes": {}},
                {"name": "identifier", "text": "old-id", "attributes": {"id": "bookid"}},
            ],
        },
    }
    document = Document(
        title="T",
        author="A",
        paragraphs=[Paragraph(id="p1", runs=[TextRun(text="Isi cerita")])],
        metadata={"epub": structure},
    )
    return document, source, cover


def test_strip_chapter_prefix_keeps_label_and_name():
    assert _strip_chapter_prefix("Bab 1: Buku Harian (Bagian 1)") == "Bab 1" + LINE_BREAK + "Buku Harian (Bagian 1)"
    assert _strip_chapter_prefix("Halo dunia") == "Halo dunia"


def test_front_page_without_text_keeps_original_xhtml(tmp_path):
    document, source, cover = _make_epub(tmp_path)
    output = tmp_path / "out.epub"
    reconstruct_epub(document, output, source_path=source)

    with ZipFile(output) as z:
        assert z.read("OEBPS/Text/cover.xhtml").decode("utf-8") == cover
        assert z.read("OEBPS/Images/cover.jpg") == b"fakejpg"
        assert "Isi cerita" in z.read("OEBPS/Text/ch1.xhtml").decode("utf-8")


def test_each_build_gets_new_identifier_and_label_from_file_name(tmp_path):
    document, source, _ = _make_epub(tmp_path)
    opfs = []
    for name in ("book_v1.epub", "book_v2.epub", "plain.epub"):
        out = tmp_path / name
        reconstruct_epub(document, out, source_path=source)
        opfs.append(ZipFile(out).read("OEBPS/content.opf").decode("utf-8"))

    assert "(IDtest1) T" in opfs[0]
    assert "(IDtest2) T" in opfs[1]
    assert "(ID) T" in opfs[2]
    ids = [re.search(r"urn:uuid:[0-9a-f-]{36}", opf).group(0) for opf in opfs]
    assert len(set(ids)) == 3
