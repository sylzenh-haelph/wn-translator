import json
from pathlib import Path

from models.document import Document, Paragraph, TextRun

from research.chapter_entity_service import ChapterEntityService
from research.entity_pipeline import EntityResearchPipeline
from research.entity_db import EntityDB
from research.adaptive_research import AdaptiveResearchEngine
from research.research_provider import (
    MockResearchProvider,
    ResearchResult,
)


# ============================================================
# CLEAN TEST FILES
# ============================================================

for path in [
    "temp/test_chapter_service_entity_db.json",
]:
    Path(path).unlink(missing_ok=True)


# ============================================================
# FAKE ENTITY AI CLIENT
# ============================================================

class FakeEntityClient:

    def generate(self, prompt):
        entity = None

        lines = prompt.splitlines()

        for index, line in enumerate(lines):
            if line.strip() == "Entity:":
                if index + 1 < len(lines):
                    entity = lines[index + 1].strip()
                break

        mapping = {
            "Alice": {
                "entity_type": "character",
                "confidence": 0.98,
                "reason": "Alice is a character.",
            },
            "Royal Palace": {
                "entity_type": "place",
                "confidence": 0.95,
                "reason": "Royal Palace is a named location.",
            },
            "Silver Sword": {
                "entity_type": "item",
                "confidence": 0.95,
                "reason": "Silver Sword is a named weapon.",
            },
        }

        return json.dumps(
            mapping.get(
                entity,
                {
                    "entity_type": "unknown",
                    "confidence": 0.0,
                    "reason": "Unknown entity.",
                },
            )
        )


# ============================================================
# FAKE RESEARCH EVALUATOR
# ============================================================

class FakeResearchClient:

    def generate(self, prompt):
        return json.dumps(
            {
                "sufficient": True,
                "confidence": 0.95,
                "selected_indices": [0],
                "reason": "Mock evidence is sufficient.",
                "needs_more_context": False,
            }
        )


def main():
    # ============================================================
    # MOCK RESEARCH PROVIDER
    # ============================================================

    research_provider = MockResearchProvider(
        results=[
            ResearchResult(
                title="Mock Entity Reference",
                url="https://example.com/entity",
                snippet="Mock research evidence.",
                source="mock",
                relevance=0.95,
            )
        ]
    )

    research_engine = AdaptiveResearchEngine(
        provider=research_provider,
        client=FakeResearchClient(),
        max_attempts=4,
    )


    # ============================================================
    # REAL ENTITY PIPELINE
    # ============================================================

    entity_db = EntityDB(
        path="temp/test_chapter_service_entity_db.json"
    )

    entity_pipeline = EntityResearchPipeline(
        db=entity_db,
        client=FakeEntityClient(),
        research_engine=research_engine,
    )


    # ============================================================
    # CHAPTER SERVICE
    # ============================================================

    service = ChapterEntityService(
        entity_pipeline=entity_pipeline,
        document_title="Chapter Service Integration Novel",
        author="Integration Author",
    )


    # ============================================================
    # CHAPTER DATA
    # ============================================================

    paragraphs = [
        Paragraph(
            id="p0001",
            runs=[
                TextRun(
                    text=(
                        "Alice enters the Royal Palace "
                        "with the Silver Sword."
                    )
                )
            ],
        ),
        Paragraph(
            id="p0002",
            runs=[
                TextRun(
                    text="Marcus waits outside."
                )
            ],
        ),
    ]


    # ============================================================
    # PROCESS CHAPTER
    # ============================================================

    print("=== CHAPTER ENTITY SERVICE ===")

    result = service.process_chapter(
        chapter_id="chapter_001",
        paragraphs=paragraphs,
    )

    print(f"Chapter: {result.chapter_id}")
    print(f"Entity count: {len(result.entities)}")

    for entity in result.entities:
        print(
            entity.text,
            "|",
            entity.entity_type,
            "|",
            entity.status,
            "|",
            entity.source_paragraph_id,
        )


    # ============================================================
    # ASSERTIONS
    # ============================================================

    assert result.chapter_id == "chapter_001"

    assert len(result.entities) == 4

    entities = {
        entity.text: entity
        for entity in result.entities
    }

    assert entities["Alice"].entity_type == "character"
    assert entities["Royal Palace"].entity_type == "place"
    assert entities["Silver Sword"].entity_type == "item"

    assert entities["Alice"].source_paragraph_id == "p0001"
    assert entities["Royal Palace"].source_paragraph_id == "p0001"
    assert entities["Silver Sword"].source_paragraph_id == "p0001"

    assert entities["Alice"].status == "researched"
    assert entities["Royal Palace"].status == "researched"
    assert entities["Silver Sword"].status == "researched"

    # Marcus is detected as a candidate but the fake AI classifier
    # intentionally has no mapping for it. The real pipeline therefore
    # preserves it as an uncertain proper noun instead of discarding it.
    assert entities["Marcus"].entity_type == "proper_noun"
    assert entities["Marcus"].status == "uncertain"
    assert entities["Marcus"].source_paragraph_id == "p0002"


    # ============================================================
    # VERIFY DATABASE
    # ============================================================

    print("\n=== DATABASE ===")

    assert entity_db.get("Alice") is not None
    assert entity_db.get("Royal Palace") is not None
    assert entity_db.get("Silver Sword") is not None

    print("Alice:", entity_db.get("Alice"))
    print("Royal Palace:", entity_db.get("Royal Palace"))
    print("Silver Sword:", entity_db.get("Silver Sword"))


    # ============================================================
    # FINAL
    # ============================================================

    print("\nPASS")


if __name__ == "__main__":
    main()
