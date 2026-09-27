from pathlib import Path

from parsers.epub_parser import parse_epub


SOURCE = Path("test_structure_fixture.epub")

if not SOURCE.exists():
    raise FileNotFoundError(
        f"{SOURCE} tidak ditemukan."
    )


document = parse_epub(SOURCE)

epub_data = document.metadata["epub"]

mapping = epub_data["paragraph_spine_map"]


print("=== PARAGRAPH → SPINE MAPPING ===")

for paragraph_id, idref in mapping.items():
    print(f"{paragraph_id} -> {idref}")


assert mapping == {
    "p0000": "chapter1",
    "p0001": "chapter1",
    "p0002": "chapter2",
    "p0003": "chapter2",
}

print("Exact mapping: PASS")


print("\n=== COVERAGE ===")

paragraph_ids = {
    paragraph.id
    for paragraph in document.paragraphs
}

assert set(mapping.keys()) == paragraph_ids

print("Every paragraph mapped: PASS")


print("\n=== SPINE ORDER ===")

spine = epub_data["spine"]

assert spine == ["chapter1", "chapter2"]

for index, idref in enumerate(spine):
    mapped_ids = [
        paragraph_id
        for paragraph_id, mapped_id in mapping.items()
        if mapped_id == idref
    ]

    print(
        idref,
        "->",
        mapped_ids,
    )

print("Spine grouping: PASS")


print("\nPASS")
