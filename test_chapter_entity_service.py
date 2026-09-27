from dataclasses import dataclass

from models.document import Paragraph, TextRun
from research.chapter_entity_service import ChapterEntityService


@dataclass
class FakeEntityResult:
    text: str
    entity_type: str
    source_paragraph_id: str
    translation: str | None = None


class FakeEntityPipeline:

    def process_text(
        self,
        text,
        source_paragraph_id,
    ):
        results = []

        if "Alice" in text:
            results.append(
                FakeEntityResult(
                    text="Alice",
                    entity_type="character",
                    source_paragraph_id=source_paragraph_id,
                    translation=None,
                )
            )

        if "Royal Palace" in text:
            results.append(
                FakeEntityResult(
                    text="Royal Palace",
                    entity_type="place",
                    source_paragraph_id=source_paragraph_id,
                    translation="Istana Kerajaan",
                )
            )

        return results


paragraphs = [
    Paragraph(
        id="p0001",
        runs=[
            TextRun(
                text="Alice enters the Royal Palace.",
            )
        ],
    ),
    Paragraph(
        id="p0002",
        runs=[
            TextRun(
                text="Marcus follows her.",
            )
        ],
    ),
]


service = ChapterEntityService(
    entity_pipeline=FakeEntityPipeline(),
)


result = service.process_chapter(
    chapter_id="chapter_001",
    paragraphs=paragraphs,
)


print("=== CHAPTER ENTITY SERVICE ===")

print("Chapter:", result.chapter_id)
print("Entity count:", len(result.entities))


for entity in result.entities:
    print(
        entity.text,
        "|",
        entity.entity_type,
        "| paragraph:",
        entity.source_paragraph_id,
        "| translation:",
        entity.translation,
    )


assert result.chapter_id == "chapter_001"

assert len(result.entities) == 2

assert result.entities[0].text == "Alice"
assert result.entities[0].entity_type == "character"
assert result.entities[0].source_paragraph_id == "p0001"

assert result.entities[1].text == "Royal Palace"
assert result.entities[1].entity_type == "place"
assert result.entities[1].source_paragraph_id == "p0001"
assert result.entities[1].translation == "Istana Kerajaan"


print("\nPASS")
