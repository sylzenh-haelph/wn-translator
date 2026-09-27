import shutil
from pathlib import Path
from zipfile import ZipFile, ZIP_STORED

from parsers.document_loader import load_document
from translation.chapter_splitter import DocumentChapterSplitter
from translation.orchestrator import TranslationOrchestrator
from translation.chapter_processor import ChapterProcessor
from storage.progress_db import ProgressDB


TEST_DIR = Path("epub_orchestrator_test")

if TEST_DIR.exists():
    shutil.rmtree(TEST_DIR)

TEST_DIR.mkdir(parents=True)


EPUB_PATH = TEST_DIR / "test_book.epub"
PROGRESS_DIR = TEST_DIR / "progress"


# ============================================================
# CREATE TEST EPUB
# ============================================================

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

        <dc:title>Integration Test Novel</dc:title>
        <dc:creator>Integration Author</dc:creator>

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
<html xmlns="http://www.w3.org/1999/xhtml">

<body>

<h1>Chapter 1</h1>

<p>Alice enters the Royal Palace.</p>

<p>Marcus follows her.</p>

</body>

</html>
"""


chapter2_xhtml = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">

<body>

<h1>Chapter 2</h1>

<p>They enter the hall.</p>

</body>

</html>
"""


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


# ============================================================
# LOAD DOCUMENT
# ============================================================

print("=== LOAD DOCUMENT ===")

document = load_document(EPUB_PATH)

print("Title:", document.title)
print("Author:", document.author)
print("Paragraphs:", len(document.paragraphs))

assert document.title == "Integration Test Novel"
assert document.author == "Integration Author"
assert len(document.paragraphs) == 5


# ============================================================
# SPLIT CHAPTERS
# ============================================================

print("\n=== CHAPTER SPLITTER ===")

splitter = DocumentChapterSplitter()
chapters = splitter.split(document)

print("Chapter count:", len(chapters))

for chapter in chapters:
    print(
        chapter.chapter_id,
        "|",
        chapter.title,
        "| paragraphs:",
        len(chapter.paragraphs),
    )

assert len(chapters) == 2

assert chapters[0].chapter_id == "chapter_001"
assert chapters[0].title == "Chapter 1"

assert chapters[1].chapter_id == "chapter_002"
assert chapters[1].title == "Chapter 2"

assert [
    paragraph.text.strip()
    for paragraph in chapters[0].paragraphs
] == [
    "Alice enters the Royal Palace.",
    "Marcus follows her.",
]

assert [
    paragraph.text.strip()
    for paragraph in chapters[1].paragraphs
] == [
    "They enter the hall.",
]


# ============================================================
# FAKE TRANSLATION ENGINE
# ============================================================

class FakeTranslationEngine:

    def translate(
        self,
        chunk,
        chapter_context,
        context_state,
        entity_resolutions=None,
    ):
        from translation.translation_engine import TranslationResult
        from translation.chapter_context import ContextState

        translations = {
            "Alice enters the Royal Palace.": (
                "Alice memasuki Istana Kerajaan."
            ),
            "Marcus follows her.": (
                "Marcus mengikutinya."
            ),
            "They enter the hall.": (
                "Mereka memasuki aula."
            ),
        }

        translation = translations.get(
            chunk.text,
            chunk.text,
        )

        return TranslationResult(
            chunk_id=chunk.chunk_id,
            translation=translation,
            context_state=ContextState(
                scene="test scene",
                active_characters=["Alice", "Marcus"],
                current_situation="test situation",
                references=[],
                style_state={},
            ),
            raw_response={},
        )


# ============================================================
# QA
# ============================================================

def fake_qa(
    source_text,
    translation,
    preserved_entities=None,
):
    from qa.rule_based_qa import run_qa

    return run_qa(
        source_text=source_text,
        translation=translation,
        preserved_entities=preserved_entities,
    )


# ============================================================
# BUILD PIPELINE
# ============================================================

print("\n=== ORCHESTRATOR ===")

progress_db = ProgressDB(
    progress_dir=PROGRESS_DIR,
)

retry_controller = __import__(
    "qa.retry_controller",
    fromlist=["RetryController"],
).RetryController(
    translation_engine=FakeTranslationEngine(),
    qa_function=fake_qa,
    max_retries=2,
)

chapter_processor = ChapterProcessor(
    retry_controller=retry_controller,
    progress_db=progress_db,
)

orchestrator = TranslationOrchestrator(
    chapter_processor=chapter_processor,
    max_tokens=1000,
)


# ============================================================
# PROCESS DOCUMENT
# ============================================================

result = orchestrator.process_document(document)

print("Document:", result.title)
print("Author:", result.author)
print("Chapters:", result.chapter_count)

assert result.title == "Integration Test Novel"
assert result.author == "Integration Author"
assert result.chapter_count == 2


# ============================================================
# VERIFY CHAPTER RESULTS
# ============================================================

print("\n=== RESULTS ===")

for chapter_result in result.chapters:

    print(
        chapter_result.chapter_id,
        "| chunks:",
        chapter_result.chunk_count,
        "| status:",
        chapter_result.status,
    )

    for processed in chapter_result.processed_chunks:
        print(
            " ",
            processed.chunk_id,
            "|",
            processed.translation,
            "| attempts:",
            processed.attempts,
            "| QA:",
            processed.qa_passed,
        )

        assert processed.qa_passed is True
        assert processed.flagged is False
        assert processed.attempts == 1


assert result.chapters[0].chunk_count == 1
assert result.chapters[1].chunk_count == 1


# ============================================================
# VERIFY PROGRESS FILES
# ============================================================

print("\n=== PROGRESS ===")

progress_files = sorted(
    PROGRESS_DIR.glob("*.json")
)

print(
    "Progress files:",
    [file.name for file in progress_files],
)

assert len(progress_files) == 2

chapter1_progress = progress_db.load(
    "chapter_001"
)

chapter2_progress = progress_db.load(
    "chapter_002"
)

assert chapter1_progress["status"] == "completed"
assert chapter2_progress["status"] == "completed"

assert len(
    chapter1_progress["completed_chunks"]
) == 1

assert len(
    chapter2_progress["completed_chunks"]
) == 1


print("\nPASS")

shutil.rmtree(TEST_DIR)
