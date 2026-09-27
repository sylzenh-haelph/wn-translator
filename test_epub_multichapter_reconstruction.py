from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from parsers.epub_parser import parse_epub
from reconstruction.epub_reconstructor import reconstruct_epub


SOURCE = Path("test_structure_fixture.epub")
OUTPUT = Path("test_multichapter_output.epub")


if not SOURCE.exists():
    raise FileNotFoundError(
        f"{SOURCE} tidak ditemukan."
    )

if OUTPUT.exists():
    OUTPUT.unlink()


print("=== LOAD SOURCE ===")

source = parse_epub(SOURCE)

print("Title:", source.title)
print("Author:", source.author)
print("Paragraphs:", len(source.paragraphs))

assert len(source.paragraphs) == 4


print("\n=== SOURCE STRUCTURE ===")

source_epub = source.metadata["epub"]

assert source_epub["spine"] == [
    "chapter1",
    "chapter2",
]

assert source_epub["paragraph_spine_map"] == {
    "p0000": "chapter1",
    "p0001": "chapter1",
    "p0002": "chapter2",
    "p0003": "chapter2",
}

print("Source structure: PASS")


print("\n=== RECONSTRUCT ===")

reconstruct_epub(
    source,
    OUTPUT,
)

assert OUTPUT.exists()
assert OUTPUT.stat().st_size > 0

print("Output:", OUTPUT)
print("File creation: PASS")


print("\n=== ZIP STRUCTURE ===")

with ZipFile(OUTPUT, "r") as epub:
    names = epub.namelist()

    print("Files:")

    for name in names:
        print(" -", name)

    assert names[0] == "mimetype"
    assert "META-INF/container.xml" in names
    assert "OEBPS/content.opf" in names
    assert "OEBPS/chapter1.xhtml" in names
    assert "OEBPS/chapter2.xhtml" in names

    assert "OEBPS/content.xhtml" not in names

    chapter1 = epub.read(
        "OEBPS/chapter1.xhtml"
    ).decode("utf-8")

    chapter2 = epub.read(
        "OEBPS/chapter2.xhtml"
    ).decode("utf-8")

    assert "Alice enters." in chapter1
    assert "Chapter 1" in chapter1

    assert "Marcus follows." in chapter2
    assert "Chapter 2" in chapter2

print("Chapter files: PASS")


print("\n=== OPF ===")

with ZipFile(OUTPUT, "r") as epub:
    opf_data = epub.read(
        "OEBPS/content.opf"
    )

root = ET.fromstring(opf_data)

manifest_ids = []
spine_ids = []

for element in root.iter():
    tag = element.tag.split("}")[-1]

    if tag == "item":
        manifest_ids.append(
            element.attrib.get("id")
        )

    elif tag == "itemref":
        spine_ids.append(
            element.attrib.get("idref")
        )

assert "chapter1" in manifest_ids
assert "chapter2" in manifest_ids

assert spine_ids == [
    "chapter1",
    "chapter2",
]

print("Manifest: PASS")
print("Spine: PASS")


print("\n=== RELOAD OUTPUT ===")

reloaded = parse_epub(OUTPUT)

assert reloaded.title == source.title
assert reloaded.author == source.author

assert [
    paragraph.text
    for paragraph in reloaded.paragraphs
] == [
    paragraph.text
    for paragraph in source.paragraphs
]

print("Content round-trip: PASS")


print("\n=== CLEANUP ===")

OUTPUT.unlink()

assert not OUTPUT.exists()

print("Cleanup: PASS")


print("\nPASS")
