from types import SimpleNamespace
import main

from main import process_chapters
from models.document import Document, Paragraph, TextRun


class FakeEntityService:
    def __init__(self):
        self.calls = []

    def process_chapter(self, chapter_id, paragraphs):
        self.calls.append({
            "chapter_id": chapter_id,
            "paragraph_count": len(paragraphs),
        })

        entity = SimpleNamespace(
            text="Silver Gate",
            entity_type="place",
            status="researched",
            source="mock",
        )

        return SimpleNamespace(
            chapter_id=chapter_id,
            entities=[entity],
        )


class FakeProcessor:
    def __init__(self):
        self.calls = []
        self.translation_engine = SimpleNamespace(
            client=SimpleNamespace()
        )

    def process_chapter(
        self,
        chapter_id,
        chunks,
        chapter_context,
        initial_context_state,
        entity_resolutions=None,
    ):
        self.calls.append({
            "chapter_id": chapter_id,
            "chunk_count": len(chunks),
            "entity_resolutions": entity_resolutions,
        })

        results = []

        for chunk in chunks:
            results.append(
                SimpleNamespace(
                    chunk_id=chunk.chunk_id,
                    translation=chunk.text,
                    paragraph_translations=list(
                        chunk.paragraph_texts
                    ),
                    context_state=None,
                    attempts=1,
                    qa_passed=True,
                    flagged=False,
                    issues=[],
                    cache_hit=False,
                )
            )

        return results


class FakeTitleTranslator:
    def __init__(self, client):
        self.client = client

    def translate(self, title, entity_resolutions=None):
        return f"{title} (ID)"


main.ChapterTitleTranslator = FakeTitleTranslator


document = Document(
    title="Research Wiring Test",
    author="Test Author",
    paragraphs=[
        Paragraph(
            id="p001",
            runs=[
                TextRun(
                    "Alice entered the Silver Gate."
                )
            ],
        ),
        Paragraph(
            id="p002",
            runs=[
                TextRun(
                    "The gate was heavily guarded."
                )
            ],
        ),
    ],
    metadata={},
)


entity_service = FakeEntityService()
processor = FakeProcessor()

results, stats = process_chapters(
    document=document,
    processor=processor,
    config=SimpleNamespace(
        max_chunk_tokens=1200,
    ),
    logger=None,
    entity_service=entity_service,
)


assert len(entity_service.calls) == 1, (
    f"Expected 1 entity-service call, "
    f"got {len(entity_service.calls)}"
)

assert len(processor.calls) == 1, (
    f"Expected 1 processor call, "
    f"got {len(processor.calls)}"
)

passed_entities = processor.calls[0][
    "entity_resolutions"
]

assert passed_entities is not None, (
    "entity_resolutions is None"
)

assert len(passed_entities) == 1, (
    f"Expected 1 resolved entity, "
    f"got {len(passed_entities)}"
)

entity = passed_entities[0]

assert entity.text == "Silver Gate"
assert entity.entity_type == "place"
assert entity.status == "researched"
assert entity.source == "mock"

assert len(results) == 1

print()
print("=== PRODUCTION RESEARCH WIRING TEST ===")
print("Entity service call : PASS")
print("Entity resolution   : PASS")
print("Processor receives  : PASS")
print("Research metadata   : PASS")
print("Chapter processing  : PASS")
print()
print("PRODUCTION RESEARCH WIRING: PASS")
