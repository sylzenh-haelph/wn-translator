from pathlib import Path
import json

from parsers.epub_parser import parse_epub


SOURCE = Path("test_structure_fixture.epub")

if not SOURCE.exists():
    raise FileNotFoundError(
        f"{SOURCE} tidak ditemukan."
    )


print("=== PARSE EPUB ===")

document = parse_epub(SOURCE)

print("Title:", document.title)
print("Author:", document.author)
print("Paragraphs:", len(document.paragraphs))

assert document.title == "Structure Test"
assert document.author == "Test Author"
assert len(document.paragraphs) == 4

print("Basic parsing: PASS")


print("\n=== EPUB METADATA ===")

epub_data = document.metadata.get("epub")

assert epub_data is not None
assert isinstance(epub_data, dict)

assert "opf_path" in epub_data
assert "manifest" in epub_data
assert "spine" in epub_data

print("epub metadata: PASS")


print("\n=== OPF ===")

print("OPF:", epub_data["opf_path"])

assert epub_data["opf_path"] == "OEBPS/content.opf"

print("OPF path: PASS")


print("\n=== MANIFEST ===")

manifest = epub_data["manifest"]

assert "chapter1" in manifest
assert "chapter2" in manifest

assert manifest["chapter1"]["href"] == "chapter1.xhtml"
assert manifest["chapter1"]["media_type"] == "application/xhtml+xml"

assert manifest["chapter2"]["href"] == "chapter2.xhtml"
assert manifest["chapter2"]["media_type"] == "application/xhtml+xml"

print("chapter1 manifest entry: PASS")
print("chapter2 manifest entry: PASS")


print("\n=== SPINE ===")

spine = epub_data["spine"]

print("Spine:", spine)

assert spine == ["chapter1", "chapter2"]

print("Spine order: PASS")


print("\n=== PARAGRAPH ORDER ===")

expected = [
    "Chapter 1",
    "Alice enters.",
    "Chapter 2",
    "Marcus follows.",
]

actual = [
    paragraph.text
    for paragraph in document.paragraphs
]

assert actual == expected

print("Spine → paragraph order: PASS")


print("\n=== JSON SERIALIZATION ===")

json.dumps(epub_data, ensure_ascii=False)

print("JSON serialization: PASS")


print("\nPASS")
