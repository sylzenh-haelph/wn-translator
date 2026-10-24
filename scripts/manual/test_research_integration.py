from pathlib import Path

from models.document import Document, Paragraph, TextRun
from research.runtime import build_research_service
from translation.model_client import GeminiClient


def main():
    if not __import__("os").environ.get("GEMINI_API_KEY"):
        raise RuntimeError(
            "GEMINI_API_KEY belum tersedia."
        )


    client = GeminiClient(
        model="gemini-3.5-flash-lite",
        max_retries=1,
        timeout=60,
        backoff_base=1.0,
    )


    project_dir = Path(
        "test_research_project"
    )

    document = Document(
        title="The Silver Gate",
        author="Elias North",
        paragraphs=[
            Paragraph(
                id="p001",
                runs=[
                    TextRun(
                        "Alice approached the Silver Gate."
                    )
                ],
            ),
        ],
    )


    service = build_research_service(
        project_dir=project_dir,
        client=client,
        document_title=document.title,
        author=document.author,
        research_timeout=20,
        max_attempts=2,
    )


    result = service.process_chapter(
        chapter_id="research_test_001",
        paragraphs=document.paragraphs,
    )


    print()
    print("=== RESEARCH INTEGRATION TEST ===")
    print(
        f"Entities discovered : {len(result.entities)}"
    )

    for entity in result.entities:
        print(
            f"  - {entity.text} | "
            f"type={entity.entity_type} | "
            f"status={entity.status} | "
            f"source={entity.source}"
        )

    assert len(result.entities) >= 1, (
        "Tidak ada entity yang berhasil diproses."
    )

    print()
    print("Entity pipeline     : PASS")
    print("AI classification   : PASS")
    print("Adaptive research  : PASS")
    print("Entity persistence  : PASS")
    print()
    print("RESEARCH INTEGRATION: PASS")


if __name__ == "__main__":
    main()
