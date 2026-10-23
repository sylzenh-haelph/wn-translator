from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapterSplitter


def test_docx_without_headings_uses_document_title():
    doc = Document(
        title="Judul Dokumen",
        author="",
        paragraphs=[Paragraph(id="p1", runs=[TextRun(text="Isi cerita")], style={})],
        metadata={},
    )
    chapters = DocumentChapterSplitter().split(doc)
    assert len(chapters) == 1
    assert chapters[0].title == "Judul Dokumen"
