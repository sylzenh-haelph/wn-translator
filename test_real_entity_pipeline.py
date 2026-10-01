from pathlib import Path

from models.document import Document, Paragraph, TextRun
from research.entity_pipeline import EntityResearchPipeline
from research.entity_db import EntityDB
from research.adaptive_research import AdaptiveResearchEngine
from research.research_provider import DuckDuckGoResearchProvider
from translation.model_client import GeminiClient


# ============================================================
# CLEAN TEST DATA
# ============================================================


def main():
    for path in [
        "temp/test_real_entity_db.json",
    ]:
        Path(path).unlink(missing_ok=True)


# ============================================================
# TEST DOCUMENT
# ============================================================

    document = Document(
        title="Integration Test Novel",
        author="Integration Author",
        paragraphs=[
            Paragraph(
                id="p0000",
                runs=[
                    TextRun(
                        text=(
                            "Alice enters the Royal Palace "
                            "with the Silver Sword."
                        )
                    )
                ],
            )
        ],
    )


# ============================================================
# REAL GEMINI CLIENT
# ============================================================

    client = GeminiClient(
        model="gemini-3.5-flash-lite"
    )


# ============================================================
# REAL WEB RESEARCH PROVIDER
# ============================================================

    research_provider = DuckDuckGoResearchProvider(
        timeout=20,
        max_retries=2,
        retry_delay=1.5,
    )


    research_engine = AdaptiveResearchEngine(
        provider=research_provider,
        client=client,
        max_attempts=4,
    )


# ============================================================
# ENTITY DATABASE
# ============================================================

    entity_db = EntityDB(
        path="temp/test_real_entity_db.json"
    )


# ============================================================
# REAL ENTITY RESEARCH PIPELINE
# ============================================================

    pipeline = EntityResearchPipeline(
        db=entity_db,
        client=client,
        research_engine=research_engine,
    )


# ============================================================
# RUN
# ============================================================

    print("=== REAL ENTITY PIPELINE ===")
    print()

    result = pipeline.process_document(document)


# ============================================================
# SUMMARY
# ============================================================

    print(f"Entity count: {len(result.entities)}")
    print(f"New entities: {result.new_entities}")
    print(f"Researched entities: {result.researched_entities}")
    print(f"Failed research: {result.failed_research}")
    print()


    for entity in result.entities:
        print(
            entity.text,
            "|",
            entity.entity_type,
            "|",
            entity.status,
            "|",
            entity.translation,
        )


# ============================================================
# BASIC ASSERTIONS
# ============================================================

    assert len(result.entities) > 0, (
        "Gemini entity extraction returned zero entities."
    )


# ============================================================
# EXPECTED TEST ENTITIES
# ============================================================

    entities = {
        entity.text.casefold(): entity
        for entity in result.entities
    }


    expected_entities = {
        "alice",
        "royal palace",
        "silver sword",
    }


    missing = [
        name
        for name in expected_entities
        if name not in entities
    ]


    if missing:
        print()
        print("WARNING: Expected entities missing:")
        for name in missing:
            print(f"- {name}")


# ============================================================
# DATABASE VALIDATION
# ============================================================

    print()
    print("=== ENTITY DATABASE ===")


    for entity in result.entities:
        record = entity_db.get(entity.text)

        assert record is not None, (
            f"Entity {entity.text!r} was not saved to EntityDB."
        )

        print(
            entity.text,
            "|",
            record["entity_type"],
            "|",
            "research=",
            len(record.get("research", [])),
            "|",
            "research_failed=",
            record.get("research_failed"),
        )


# ============================================================
# RESEARCH VALIDATION
# ============================================================

    researched_count = sum(
        1
        for entity in result.entities
        if entity.status == "researched"
    )

    failed_count = sum(
        1
        for entity in result.entities
        if entity.status == "research_failed"
    )


    print()
    print("=== PIPELINE RESULT ===")
    print(f"Extracted: {len(result.entities)}")
    print(f"Researched: {researched_count}")
    print(f"Research failed: {failed_count}")


    assert researched_count > 0, (
        "No extracted entity reached successful research."
    )


    print()
    print("REAL ENTITY PIPELINE: PASS")


if __name__ == "__main__":
    main()
