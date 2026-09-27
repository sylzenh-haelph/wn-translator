from pathlib import Path

from models.document import Document, Paragraph, TextRun
from research.entity_db import EntityDB
from research.entity_pipeline import EntityResearchPipeline


class FakeClient:
    pass


class FakeResearchEngine:
    def research(
        self,
        entity_text,
        entity_type,
        novel_title,
        author,
        chapter_context,
    ):
        class Evidence:
            title = "Example Novel Wiki"
            url = "https://example.com/example-novel"
            snippet = (
                "The Silver Sword is a named weapon "
                "used by the protagonist."
            )
            source = "example.com"

        # Simpan nilai method ke variabel lokal terlebih dahulu.
        result_entity_text = entity_text
        result_entity_type = entity_type
        result_query = (
            f'"{entity_text}" {entity_type} '
            f'"{novel_title}"'
        )

        class Result:
            success = True
            confidence = 0.95
            evidence = [Evidence()]
            attempts = 1
            reason = "Sufficient evidence found."
            research_failed = False

        # Isi attribute setelah class dibuat.
        result = Result()
        result.entity_text = result_entity_text
        result.entity_type = result_entity_type
        result.final_query = result_query

        return result


class FakeClassification:
    def __init__(self, entity_type, confidence, reason):
        self.entity_type = entity_type
        self.confidence = confidence
        self.reason = reason


def fake_classify(client, candidate, context):
    if candidate.text == "Silver Sword":
        return FakeClassification(
            entity_type="item",
            confidence=0.95,
            reason="Named weapon in the story.",
        )

    return FakeClassification(
        entity_type="character",
        confidence=0.95,
        reason="Personal name used as a character.",
    )


import research.entity_pipeline as pipeline_module

pipeline_module.classify_with_ai = fake_classify


def main():
    db_path = Path("temp/test_pipeline_db.json")

    if db_path.exists():
        db_path.unlink()

    db = EntityDB(db_path)

    document = Document(
        title="Example Novel",
        author="Example Author",
        paragraphs=[
            Paragraph(
                id="p0000",
                runs=[
                    TextRun(
                        "The Silver Sword was lying on the table."
                    )
                ],
            )
        ],
    )

    pipeline = EntityResearchPipeline(
        db=db,
        client=FakeClient(),
        research_engine=FakeResearchEngine(),
    )

    result = pipeline.process_document(document)

    print("=== PIPELINE RESULT ===")

    for entity in result.entities:
        print(
            entity.text,
            "->",
            entity.entity_type,
            "->",
            entity.status,
        )

    print("New entities       :", result.new_entities)
    print("Researched entities:", result.researched_entities)
    print("Failed research   :", result.failed_research)

    record = db.get("Silver Sword")

    print("\n=== DB RECORD ===")
    print(record)

    assert record is not None
    assert record["entity_type"] == "item"
    assert len(record["research"]) == 1
    assert result.new_entities == 1
    assert result.researched_entities == 1
    assert result.failed_research == 0

    print("\nPASS")


if __name__ == "__main__":
    main()
