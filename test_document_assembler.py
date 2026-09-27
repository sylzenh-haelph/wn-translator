from models.document import Document, Paragraph, TextRun
from translation.chapter_reconstructor import ReconstructedChapter
from translation.document_assembler import DocumentAssembler


source_document = Document(
    title="Integration Novel",
    author="Test Author",
    metadata={
        "language": "en",
        "identifier": "test-novel-001",
    },
)


chapter_1_heading = Paragraph(
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
)


chapter_1 = ReconstructedChapter(
    chapter_id="chapter_001",
    title="Chapter 1",
    heading=chapter_1_heading,
    paragraphs=[
        Paragraph(
            id="p0001",
            runs=[
                TextRun(
                    text="Alice memasuki istana.",
                    formatting={"bold": True},
                )
            ],
            style={"alignment": "left"},
        ),
        Paragraph(
            id="p0002",
            runs=[
                TextRun(
                    text="Marcus mengikutinya.",
                    formatting={"italic": True},
                )
            ],
            style={"alignment": "left"},
        ),
    ],
)


chapter_2_heading = Paragraph(
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
)


chapter_2 = ReconstructedChapter(
    chapter_id="chapter_002",
    title="Chapter 2",
    heading=chapter_2_heading,
    paragraphs=[
        Paragraph(
            id="p0004",
            runs=[
                TextRun(
                    text="Mereka memasuki aula utama.",
                    formatting={},
                )
            ],
            style={"alignment": "left"},
        ),
    ],
)


assembler = DocumentAssembler()

print("=== ASSEMBLE DOCUMENT ===")

result = assembler.assemble(
    source_document=source_document,
    chapter_results=[
        chapter_1,
        chapter_2,
    ],
)

print("Title:", result.title)
print("Author:", result.author)
print("Paragraphs:", len(result.paragraphs))


print("\n=== ORDER ===")

expected_ids = [
    "p0000",
    "p0001",
    "p0002",
    "p0003",
    "p0004",
]

actual_ids = [
    paragraph.id
    for paragraph in result.paragraphs
]

assert actual_ids == expected_ids

print("Paragraph order: PASS")
print("Chapter order: PASS")


print("\n=== CONTENT ===")

expected_texts = [
    "Chapter 1",
    "Alice memasuki istana.",
    "Marcus mengikutinya.",
    "Chapter 2",
    "Mereka memasuki aula utama.",
]

actual_texts = [
    paragraph.text
    for paragraph in result.paragraphs
]

assert actual_texts == expected_texts

print("Content order: PASS")


print("\n=== HEADING ===")

assert result.paragraphs[0].style["heading_level"] == 1
assert result.paragraphs[0].style["alignment"] == "center"
assert result.paragraphs[0].runs[0].formatting["bold"] is True

assert result.paragraphs[3].style["heading_level"] == 1
assert result.paragraphs[3].runs[0].formatting["font_size"] == 18

print("Heading preservation: PASS")


print("\n=== FORMATTING ===")

assert result.paragraphs[1].runs[0].formatting["bold"] is True
assert result.paragraphs[2].runs[0].formatting["italic"] is True

print("Body formatting: PASS")


print("\n=== METADATA ===")

assert result.title == "Integration Novel"
assert result.author == "Test Author"
assert result.metadata["language"] == "en"
assert result.metadata["identifier"] == "test-novel-001"

print("Metadata preservation: PASS")


print("\n=== ID VALIDATION ===")

assert len(actual_ids) == len(set(actual_ids))

print("Unique paragraph IDs: PASS")


print("\nPASS")
