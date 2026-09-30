import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

from parsers.document_loader import load_document


TEST_DIR = Path("epub_loader_test")

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)

TEST_DIR.mkdir(parents=True)


EPUB_PATH = TEST_DIR / "test_book.epub"


# ----------------------------------------
# EPUB FILE STRUCTURE
# ----------------------------------------

container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container
    version="1.0"
    xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
    <rootfiles>
        <rootfile
            full-path="OEBPS/content.opf"
            media-type="application/oebps-package+xml"/>
    </rootfiles>
</container>
"""


opf_xml = """<?xml version="1.0" encoding="UTF-8"?>
<package
    xmlns="http://www.idpf.org/2007/opf"
    version="3.0">

    <metadata
        xmlns:dc="http://purl.org/dc/elements/1.1/">

        <dc:title>Test EPUB Novel</dc:title>
        <dc:creator>Test Author</dc:creator>

    </metadata>

    <manifest>
        <item
            id="chapter1"
            href="chapter1.xhtml"
            media-type="application/xhtml+xml"/>

        <item
            id="chapter2"
            href="chapter2.xhtml"
            media-type="application/xhtml+xml"/>
    </manifest>

    <spine>
        <itemref idref="chapter1"/>
        <itemref idref="chapter2"/>
    </spine>

</package>
"""


chapter1_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<html
    xmlns="http://www.w3.org/1999/xhtml">

<head>
    <title>Chapter 1</title>
</head>

<body>

<h1>Chapter 1</h1>

<p>
    Alice enters the
    <strong>Royal Palace</strong>.
</p>

<p>
    Marcus follows her.
</p>

</body>
</html>
"""


chapter2_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<html
    xmlns="http://www.w3.org/1999/xhtml">

<head>
    <title>Chapter 2</title>
</head>

<body>

<h1>Chapter 2</h1>

<p>
    They enter the hall.
</p>

</body>
</html>
"""


# ----------------------------------------
# CREATE EPUB
# ----------------------------------------

with ZipFile(
    EPUB_PATH,
    "w",
    compression=ZIP_STORED,
) as epub:

    epub.writestr(
        "META-INF/container.xml",
        container_xml,
    )

    epub.writestr(
        "OEBPS/content.opf",
        opf_xml,
    )

    epub.writestr(
        "OEBPS/chapter1.xhtml",
        chapter1_xhtml,
    )

    epub.writestr(
        "OEBPS/chapter2.xhtml",
        chapter2_xhtml,
    )


# ----------------------------------------
# LOAD EPUB
# ----------------------------------------

print("=== LOAD EPUB ===")

document = load_document(EPUB_PATH)

print("Title:", document.title)
print("Author:", document.author)

print(
    "Paragraph count:",
    len(document.paragraphs),
)

assert document.title == "Test EPUB Novel"
assert document.author == "Test Author"

assert len(document.paragraphs) == 5


# ----------------------------------------
# TEXT CHECK
# ----------------------------------------

print("\n=== TEXT ===")

texts = [
    paragraph.text.strip()
    for paragraph in document.paragraphs
]

print(texts)

assert texts == [
    "Chapter 1",
    "Alice enters the Royal Palace.",
    "Marcus follows her.",
    "Chapter 2",
    "They enter the hall.",
]


# ----------------------------------------
# HEADING CHECK
# ----------------------------------------

print("\n=== HEADINGS ===")

heading_1 = document.paragraphs[0]
heading_2 = document.paragraphs[3]

print(
    heading_1.text,
    heading_1.style,
)

print(
    heading_2.text,
    heading_2.style,
)

assert heading_1.style["heading_level"] == 1

assert heading_2.style["heading_level"] == 1


# ----------------------------------------
# FORMATTING CHECK
# ----------------------------------------

print("\n=== FORMATTING ===")

paragraph = document.paragraphs[1]

for run in paragraph.runs:
    print(
        repr(run.text),
        run.formatting,
    )


bold_runs = [
    run
    for run in paragraph.runs
    if run.formatting.get("bold", False)
]

assert len(bold_runs) == 1
assert bold_runs[0].text.strip() == (
    "Royal Palace"
)


# ----------------------------------------
# SPINE ORDER CHECK
# ----------------------------------------

print("\n=== SPINE ORDER ===")

assert texts.index("Chapter 1") < (
    texts.index("Chapter 2")
)

assert texts.index(
    "Marcus follows her."
) < texts.index(
    "Chapter 2"
)

print("Spine order OK")


print("\nPASS")

shutil.rmtree(TEST_DIR)
