from models.document import Document, Paragraph, TextRun
from translation.chapter_splitter import DocumentChapterSplitter


document = Document(
    title="Test Novel",
    author="Test Author",
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
                TextRun(text="Alice enters the palace.")
            ],
        ),
        Paragraph(
            id="p0002",
            runs=[
                TextRun(text="Marcus follows her.")
            ],
        ),
    ],
)


splitter = DocumentChapterSplitter()
chapters = splitter.split(document)

print("=== HEADING PRESERVATION ===")

chapter = chapters[0]

print("Title:", chapter.title)
print("Heading ID:", chapter.heading.id)
print("Heading text:", chapter.heading.text)
print("Heading style:", chapter.heading.style)
print("Heading formatting:", chapter.heading.runs[0].formatting)

assert chapter.heading is not None
assert chapter.heading.id == "p0000"
assert chapter.heading.text == "Chapter 1"
assert chapter.heading.style["heading_level"] == 1
assert chapter.heading.style["alignment"] == "center"
assert chapter.heading.runs[0].formatting["bold"] is True
assert chapter.heading.runs[0].formatting["font_size"] == 18

print("\n=== BODY SEPARATION ===")

print("Body IDs:", [p.id for p in chapter.paragraphs])

assert [p.id for p in chapter.paragraphs] == [
    "p0001",
    "p0002",
]

assert all(
    p.id != chapter.heading.id
    for p in chapter.paragraphs
)

print("\nPASS")
