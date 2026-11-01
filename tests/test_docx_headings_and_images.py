from pathlib import Path
import base64
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docx import Document as DocxDocument

from models.document import Document, Paragraph
from parsers.docx_parser import parse_docx
from reconstruction.docx_reconstructor import reconstruct_docx
from translation.chapter_splitter import DocumentChapterSplitter

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def test_two_heading1_split_into_chapters(tmp_path):
    path = tmp_path / "novel.docx"
    d = DocxDocument()
    d.add_heading("Bab 1", level=1)
    d.add_paragraph("satu")
    d.add_heading("Bab 2", level=1)
    d.add_paragraph("dua")
    d.save(path)
    chapters = DocumentChapterSplitter().split(parse_docx(path))
    assert [c.title for c in chapters] == ["Bab 1", "Bab 2"]


def test_single_heading_keeps_document_title(tmp_path):
    path = tmp_path / "novel.docx"
    d = DocxDocument()
    d.add_heading("Bab 1", level=1)
    d.add_paragraph("satu")
    d.save(path)
    chapters = DocumentChapterSplitter().split(parse_docx(path))
    assert len(chapters) == 1
    assert chapters[0].title == "novel"


def test_docx_output_keeps_images(tmp_path):
    out = tmp_path / "out.docx"
    document = Document(
        title="T",
        author="",
        paragraphs=[Paragraph(id="p0000", runs=[], style={"images": ["p0000_0.png"]})],
        metadata={"docx_images": {"p0000_0.png": PNG}},
    )
    reconstruct_docx(document, out)
    assert len(DocxDocument(out).inline_shapes) == 1
