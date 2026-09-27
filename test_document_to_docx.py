from pathlib import Path

from models.document import Document, Paragraph, TextRun
from translation.document_assembler import DocumentAssembler
from reconstruction.docx_reconstructor import reconstruct_docx
from parsers.docx_parser import parse_docx


OUTPUT = Path("test_output_document.docx")

if OUTPUT.exists():
    OUTPUT.unlink()


print("=== SOURCE DOCUMENT ===")

source_document = Document(
    title="Translated Integration Novel",
    author="Test Author",
    metadata={
        "language": "id",
        "identifier": "integration-test",
    },
    paragraphs=[
        Paragraph(
            id="p0000",
            runs=[
                TextRun(
                    text="Chapter 1",
                    formatting={
                        "bold": True,
                        "font_size": 18,
                    },
                )
            ],
            style={
                "heading_level": 1,
                "alignment": "center",
            },
        ),
        Paragraph(
            id="p0001",
            runs=[
                TextRun(
                    text="Alice memasuki istana.",
                    formatting={
                        "bold": True,
                        "font_name": "Arial",
                        "font_size": 12,
                    },
                )
            ],
            style={
                "alignment": "left",
            },
        ),
        Paragraph(
            id="p0002",
            runs=[
                TextRun(
                    text="Marcus mengikutinya.",
                    formatting={
                        "italic": True,
                    },
                )
            ],
            style={
                "alignment": "left",
            },
        ),
        Paragraph(
            id="p0003",
            runs=[
                TextRun(
                    text="Chapter 2",
                    formatting={
                        "bold": True,
                        "font_size": 18,
                    },
                )
            ],
            style={
                "heading_level": 1,
                "alignment": "center",
            },
        ),
        Paragraph(
            id="p0004",
            runs=[
                TextRun(
                    text="Mereka memasuki aula utama.",
                    formatting={},
                )
            ],
            style={
                "alignment": "left",
            },
        ),
    ],
)


print("Title:", source_document.title)
print("Author:", source_document.author)
print("Paragraphs:", len(source_document.paragraphs))


print("\n=== DOCUMENT ASSEMBLER ===")

assembler = DocumentAssembler()

assembled = assembler.assemble(
    source_document=source_document,
    chapter_results=[],
)

assembled.paragraphs = source_document.paragraphs

assert len(assembled.paragraphs) == 5

print("Document assembly: PASS")


print("\n=== DOCX RECONSTRUCTION ===")

reconstruct_docx(
    assembled,
    OUTPUT,
)

assert OUTPUT.exists()
assert OUTPUT.stat().st_size > 0

print("Output:", OUTPUT)
print("File exists: PASS")
print("File size:", OUTPUT.stat().st_size, "bytes")


print("\n=== RELOAD ===")

reloaded = parse_docx(OUTPUT)

assert len(reloaded.paragraphs) == 5

print("Reload paragraph count: PASS")


print("\n=== CONTENT ===")

expected = [
    "Chapter 1",
    "Alice memasuki istana.",
    "Marcus mengikutinya.",
    "Chapter 2",
    "Mereka memasuki aula utama.",
]

actual = [
    paragraph.text
    for paragraph in reloaded.paragraphs
]

assert actual == expected

print("Content preservation: PASS")


print("\n=== FORMATTING ===")

assert (
    reloaded.paragraphs[0]
    .runs[0]
    .formatting
    .get("bold")
    is True
)

assert (
    reloaded.paragraphs[1]
    .runs[0]
    .formatting
    .get("bold")
    is True
)

assert (
    reloaded.paragraphs[2]
    .runs[0]
    .formatting
    .get("italic")
    is True
)

assert (
    reloaded.paragraphs[1]
    .runs[0]
    .formatting
    .get("font_name")
    == "Arial"
)

print("Run formatting preservation: PASS")


print("\n=== CLEANUP ===")

OUTPUT.unlink()

assert not OUTPUT.exists()

print("Temporary output removed: PASS")


print("\nPASS")
