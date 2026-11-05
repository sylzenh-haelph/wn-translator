from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zipfile import ZipFile

from models.document import Document, Paragraph, TextRun
from reconstruction.epub_reconstructor import reconstruct_epub


def test_docx_chapters_become_separate_pages_with_toc(tmp_path):
    paragraphs = [
        Paragraph(id="p1", runs=[TextRun("Bab 1: Awal")], style={"heading_level": 1}),
        Paragraph(id="p2", runs=[TextRun("isi satu")], style={}),
        Paragraph(id="p3", runs=[TextRun("Bab 2: Lanjut")], style={"heading_level": 1}),
        Paragraph(id="p4", runs=[TextRun("isi dua")], style={}),
    ]
    document = Document(title="Novel", author="", paragraphs=paragraphs, metadata={})
    out = tmp_path / "o.epub"

    reconstruct_epub(document, out)

    with ZipFile(out) as z:
        names = set(z.namelist())
        opf = z.read("OEBPS/content.opf").decode("utf-8")
        nav = z.read("OEBPS/nav-generated.xhtml").decode("utf-8")
        chapter_one = z.read("OEBPS/chapter-001.xhtml").decode("utf-8")

    assert "OEBPS/chapter-001.xhtml" in names
    assert "OEBPS/chapter-002.xhtml" in names
    assert opf.count("<itemref") == 2
    assert "Bab 1: Awal" in nav
    assert "Bab 2: Lanjut" in nav
    assert "isi satu" in chapter_one
    assert "isi dua" not in chapter_one
