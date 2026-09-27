from pathlib import Path
from zipfile import ZipFile

from models.document import Document, Paragraph, TextRun
from reconstruction.epub_reconstructor import reconstruct_epub
from parsers.epub_parser import parse_epub


OUTPUT = Path("test_output_document.epub")

if OUTPUT.exists():
    OUTPUT.unlink()


print("=== SOURCE DOCUMENT ===")

source_document = Document(
    title="EPUB Integration Novel",
    author="Test Author",
    metadata={
        "language": "id",
    },
    paragraphs=[
        Paragraph(
            id="p0000",
            runs=[
                TextRun(
                    text="Chapter 1",
                    formatting={
                        "bold": True,
                    },
                )
            ],
            style={
                "heading_level": 1,
            },
        ),
        Paragraph(
            id="p0001",
            runs=[
                TextRun(
                    text="Alice memasuki ",
                    formatting={
                        "bold": True,
                    },
                ),
                TextRun(
                    text="Royal Palace.",
                    formatting={
                        "italic": True,
                    },
                ),
            ],
            style={},
        ),
        Paragraph(
            id="p0002",
            runs=[
                TextRun(
                    text="Marcus mengikutinya.",
                    formatting={
                        "underline": True,
                    },
                )
            ],
            style={},
        ),
        Paragraph(
            id="p0003",
            runs=[
                TextRun(
                    text="Chapter 2",
                    formatting={
                        "bold": True,
                    },
                )
            ],
            style={
                "heading_level": 1,
            },
        ),
        Paragraph(
            id="p0004",
            runs=[
                TextRun(
                    text="H",
                    formatting={
                        "superscript": True,
                    },
                ),
                TextRun(
                    text="2",
                    formatting={
                        "subscript": True,
                    },
                ),
                TextRun(
                    text="O",
                    formatting={},
                ),
            ],
            style={},
        ),
    ],
)


print("Title:", source_document.title)
print("Author:", source_document.author)
print("Paragraphs:", len(source_document.paragraphs))


print("\n=== EPUB RECONSTRUCTION ===")

reconstruct_epub(
    source_document,
    OUTPUT,
)

assert OUTPUT.exists()
assert OUTPUT.stat().st_size > 0

print("Output:", OUTPUT)
print("File size:", OUTPUT.stat().st_size, "bytes")
print("File creation: PASS")


print("\n=== EPUB STRUCTURE ===")

with ZipFile(OUTPUT, "r") as epub:
    names = epub.namelist()

    assert names[0] == "mimetype"
    assert epub.read("mimetype") == b"application/epub+zip"
    assert "META-INF/container.xml" in names
    assert "OEBPS/content.opf" in names
    assert "OEBPS/content.xhtml" in names

print("mimetype: PASS")
print("container.xml: PASS")
print("content.opf: PASS")
print("content.xhtml: PASS")


print("\n=== RELOAD WITH EPUB PARSER ===")

reloaded = parse_epub(OUTPUT)

print("Title:", reloaded.title)
print("Author:", reloaded.author)
print("Paragraphs:", len(reloaded.paragraphs))

assert reloaded.title == source_document.title
assert reloaded.author == source_document.author
assert len(reloaded.paragraphs) == 5

print("Metadata preservation: PASS")
print("Paragraph count: PASS")


print("\n=== CONTENT ===")

expected = [
    "Chapter 1",
    "Alice memasuki Royal Palace.",
    "Marcus mengikutinya.",
    "Chapter 2",
    "H2O",
]

actual = [
    paragraph.text
    for paragraph in reloaded.paragraphs
]

assert actual == expected

print("Content preservation: PASS")


print("\n=== FORMATTING ===")

p1_runs = reloaded.paragraphs[1].runs
assert p1_runs[0].formatting.get("bold") is True
assert p1_runs[1].formatting.get("italic") is True

p2_runs = reloaded.paragraphs[2].runs
assert p2_runs[0].formatting.get("underline") is True

p4_runs = reloaded.paragraphs[4].runs
assert p4_runs[0].formatting.get("superscript") is True
assert p4_runs[1].formatting.get("subscript") is True

print("Bold: PASS")
print("Italic: PASS")
print("Underline: PASS")
print("Superscript: PASS")
print("Subscript: PASS")


print("\n=== CLEANUP ===")

OUTPUT.unlink()

assert not OUTPUT.exists()

print("Temporary output removed: PASS")


print("\nPASS")
