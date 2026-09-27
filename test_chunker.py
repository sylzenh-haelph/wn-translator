from models.document import Paragraph, TextRun
from translation.chunker import (
    build_chunks,
    estimate_tokens,
)


def paragraph(paragraph_id, text):
    return Paragraph(
        id=paragraph_id,
        runs=[TextRun(text=text)],
    )


print("=== TOKEN ESTIMATION ===")

text = "This is a simple sentence."

tokens = estimate_tokens(text)

print("Text  :", text)
print("Tokens:", tokens)

assert tokens > 0


print("\n=== NORMAL CHUNKING ===")

paragraphs = [
    paragraph("p0000", "Alice enters the palace."),
    paragraph("p0001", "Marcus follows her."),
    paragraph("p0002", "They begin talking."),
]

chunks = build_chunks(
    paragraphs,
    max_tokens=20,
)

for chunk in chunks:
    print(chunk)

assert len(chunks) == 1
assert chunks[0].paragraph_ids == [
    "p0000",
    "p0001",
    "p0002",
]


print("\n=== CHUNK LIMIT WITH NORMAL PARAGRAPHS ===")

paragraphs = [
    paragraph(
        "p0000",
        "Alice enters the palace."
    ),
    paragraph(
        "p0001",
        "Marcus waits outside."
    ),
]

chunks = build_chunks(
    paragraphs,
    max_tokens=10,
)

for chunk in chunks:
    print(chunk)

assert len(chunks) == 2
assert chunks[0].paragraph_ids == ["p0000"]
assert chunks[1].paragraph_ids == ["p0001"]


print("\n=== LONG PARAGRAPH FALLBACK ===")

long_text = (
    "Alice walks through the enormous royal palace "
    "while carefully observing every room and corridor "
    "because she is searching for Marcus who disappeared "
    "earlier that morning without leaving any explanation."
)

paragraphs = [
    paragraph("p0000", long_text),
]

chunks = build_chunks(
    paragraphs,
    max_tokens=10,
)

for chunk in chunks:
    print(chunk)

assert len(chunks) > 1

for chunk in chunks:
    assert chunk.paragraph_ids == ["p0000"]
    assert chunk.text.strip()


print("\n=== ORDER CHECK ===")

reconstructed = " ".join(
    chunk.text
    for chunk in chunks
)

original_words = long_text.split()
result_words = reconstructed.split()

assert result_words == original_words

print("Original words :", len(original_words))
print("Result words   :", len(result_words))


print("\nPASS")
