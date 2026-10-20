from pathlib import Path
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import reconstruct_output
from models.document import Document, Paragraph, TextRun


def test_docx_source_does_not_leak_into_epub(tmp_path):
    source = tmp_path / "novel.docx"
    with ZipFile(source, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", "<w:document/>")
    document = Document(
        title="T",
        author="A",
        paragraphs=[Paragraph(id="p1", runs=[TextRun(text="Isi")])],
        metadata={},
    )
    out = tmp_path / "out.epub"
    reconstruct_output(source, document, out)
    with ZipFile(out) as z:
        assert "word/document.xml" not in z.namelist()
