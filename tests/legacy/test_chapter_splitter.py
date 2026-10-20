import shutil
from pathlib import Path

from models.document import (
    Document,
    Paragraph,
    TextRun,
)
from translation.chapter_splitter import (
    DocumentChapterSplitter,
)


document = Document(
    title="Test Novel",
    author="Test Author",
)

document.paragraphs = [
    Paragraph(
        id="p0000",
        runs=[
            TextRun(text="Chapter 1")
        ],
        style={
            "name": "Heading 1",
            "heading_level": 1,
        },
    ),
    Paragraph(
        id="p0001",
        runs=[
            TextRun(text="Alice enters the palace.")
        ],
        style={
            "name": "Normal",
            "heading_level": None,
        },
    ),
    Paragraph(
        id="p0002",
        runs=[
            TextRun(text="Marcus follows her.")
        ],
        style={
            "name": "Normal",
            "heading_level": None,
        },
    ),
    Paragraph(
        id="p0003",
        runs=[
            TextRun(text="Chapter 2")
        ],
        style={
            "name": "Heading 1",
            "heading_level": 1,
        },
    ),
    Paragraph(
        id="p0004",
        runs=[
            TextRun(text="They enter the hall.")
        ],
        style={
            "name": "Normal",
            "heading_level": None,
        },
    ),
]


splitter = DocumentChapterSplitter()

chapters = splitter.split(document)


print("=== CHAPTER COUNT ===")
print("Count:", len(chapters))

assert len(chapters) == 2


print("\n=== CHAPTER 1 ===")
print("ID:", chapters[0].chapter_id)
print("Title:", chapters[0].title)
print(
    "Paragraphs:",
    [p.text for p in chapters[0].paragraphs],
)

assert chapters[0].chapter_id == "chapter_001"
assert chapters[0].title == "Chapter 1"
assert [
    p.text for p in chapters[0].paragraphs
] == [
    "Alice enters the palace.",
    "Marcus follows her.",
]


print("\n=== CHAPTER 2 ===")
print("ID:", chapters[1].chapter_id)
print("Title:", chapters[1].title)
print(
    "Paragraphs:",
    [p.text for p in chapters[1].paragraphs],
)

assert chapters[1].chapter_id == "chapter_002"
assert chapters[1].title == "Chapter 2"
assert [
    p.text for p in chapters[1].paragraphs
] == [
    "They enter the hall.",
]


print("\n=== PARAGRAPH IDS ===")

all_ids = [
    p.id
    for chapter in chapters
    for p in chapter.paragraphs
]

print(all_ids)

assert all_ids == [
    "p0001",
    "p0002",
    "p0004",
]


print("\nPASS")
