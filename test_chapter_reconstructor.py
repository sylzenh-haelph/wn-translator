from models.document import Paragraph, TextRun
from translation.chapter_reconstructor import ChapterReconstructor


reconstructor = ChapterReconstructor()

heading = Paragraph(
    id="p0000",
    runs=[
        TextRun(
            "Chapter 1",
            {
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

source_paragraphs = [
    Paragraph(
        id="p0001",
        runs=[
            TextRun(
                "Alice enters ",
                {
                    "bold": False,
                    "italic": False,
                },
            ),
            TextRun(
                "the Royal Palace.",
                {
                    "bold": True,
                    "italic": False,
                },
            ),
        ],
        style={
            "alignment": "left",
            "spacing_after": 8,
        },
    ),
    Paragraph(
        id="p0002",
        runs=[
            TextRun(
                "Marcus follows her.",
                {
                    "italic": True,
                },
            )
        ],
        style={
            "alignment": "left",
        },
    ),
]

translated = [
    "Alice memasuki Istana Kerajaan.",
    "Marcus mengikutinya.",
]

result = reconstructor.reconstruct(
    chapter_id="chapter_001",
    title="Chapter 1",
    source_paragraphs=source_paragraphs,
    translated_paragraphs=translated,
    heading=heading,
)

assert result.chapter_id == "chapter_001"
assert result.title == "Chapter 1"

assert result.heading is not None
assert result.heading.id == "p0000"
assert result.heading.text == "Chapter 1"
assert result.heading.style["heading_level"] == 1
assert result.heading.runs[0].formatting["bold"] is True
assert result.heading.runs[0].formatting["font_size"] == 18

assert len(result.paragraphs) == 2

assert result.paragraphs[0].id == "p0001"
assert result.paragraphs[0].text == translated[0]
assert result.paragraphs[0].style["alignment"] == "left"
assert result.paragraphs[0].style["spacing_after"] == 8

assert result.paragraphs[1].id == "p0002"
assert result.paragraphs[1].text == translated[1]
assert result.paragraphs[1].runs[0].formatting["italic"] is True

# Multi-run formatting must survive.
assert len(result.paragraphs[0].runs) == 2
assert result.paragraphs[0].runs[0].formatting["bold"] is False
assert result.paragraphs[0].runs[1].formatting["bold"] is True

# Paragraph count mismatch must be rejected.
try:
    reconstructor.reconstruct(
        chapter_id="chapter_001",
        title="Chapter 1",
        source_paragraphs=source_paragraphs,
        translated_paragraphs=["Only one paragraph."],
        heading=heading,
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "Paragraph count mismatch should raise ValueError."
    )

print("=== RECONSTRUCTOR ===")
print("Chapter:", result.chapter_id)
print("Heading:", result.heading.text)
print("Paragraphs:", len(result.paragraphs))

for paragraph in result.paragraphs:
    print(
        paragraph.id,
        "|",
        paragraph.text,
        "| runs:",
        len(paragraph.runs),
    )

print("=== CHECKS ===")
print("Heading preserved: PASS")
print("Paragraph IDs preserved: PASS")
print("Paragraph styles preserved: PASS")
print("Run formatting preserved: PASS")
print("Paragraph count validation: PASS")
print("PASS")
