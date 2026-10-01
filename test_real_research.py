from pathlib import Path
from tempfile import TemporaryDirectory

from research.entity_db import EntityDB
from research.research_provider import DuckDuckGoResearchProvider
from research.adaptive_research import AdaptiveResearchEngine
from translation.model_client import GeminiClient


def main():
    with TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        db = EntityDB(tmp / "entities.json")

        provider = DuckDuckGoResearchProvider(timeout=20)

        client = GeminiClient(model="gemini-3.5-flash-lite")

        engine = AdaptiveResearchEngine(
            provider=provider,
            client=client,
            max_attempts=3,
        )

        result = engine.research(
            entity_text="Oxford University",
            entity_type="organization",
            novel_title="Research Integration Test",
            author="Test Author",
            chapter_context=(
                "The character studied at Oxford University before "
                "returning to the kingdom."
            ),
        )

        print("=== REAL RESEARCH INTEGRATION TEST ===")
        print(f"Success: {result.success}")
        print(f"Entity: {result.entity_text}")
        print(f"Type: {result.entity_type}")
        print(f"Final query: {result.final_query}")
        print(f"Attempts: {result.attempts}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Research failed: {result.research_failed}")
        print(f"Evidence count: {len(result.evidence)}")

        for i, evidence in enumerate(result.evidence, 1):
            print()
            print(f"[Evidence {i}]")
            print(f"Title: {evidence.title}")
            print(f"URL: {evidence.url}")
            print(f"Source: {evidence.source}")
            print(f"Snippet: {evidence.snippet[:300]}")

        print()

        if result.success and result.evidence:
            print("REAL RESEARCH INTEGRATION: PASS")
        else:
            print("REAL RESEARCH INTEGRATION: NO POSITIVE RESULT")
            print("Possible temporary search/model availability issue.")


if __name__ == "__main__":
    main()
