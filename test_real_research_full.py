from pathlib import Path
from tempfile import TemporaryDirectory

from translation.model_client import GeminiClient
from research.entity_db import EntityDB
from research.research_provider import DuckDuckGoResearchProvider
from research.adaptive_research import AdaptiveResearchEngine
from research.evidence_validator import EvidenceValidator


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

    print("=== ADAPTIVE RESEARCH ===")
    print(f"Success: {result.success}")
    print(f"Entity: {result.entity_text}")
    print(f"Type: {result.entity_type}")
    print(f"Final query: {result.final_query}")
    print(f"Attempts: {result.attempts}")
    print(f"Confidence: {result.confidence}")
    print(f"Evidence count: {len(result.evidence)}")

    if not result.success or not result.evidence:
        print()
        print("ADAPTIVE RESEARCH: FAIL")
        raise SystemExit(1)

    validator = EvidenceValidator()

    validation = validator.validate(
        entity_text=result.entity_text,
        entity_type=result.entity_type,
        evidence=result.evidence,
    )

    print()
    print("=== EVIDENCE VALIDATION ===")
    print(validation)

    if not validation.valid:
        print()
        print("EVIDENCE VALIDATION: FAIL")
        raise SystemExit(1)

    print()
    print("=== ENTITY DB WRITE ===")

    db.add_research(
        entity_type=result.entity_type,
        canonical_name=result.entity_text,
        evidence=[
            {
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "source": item.source,
            }
            for item in result.evidence
        ],
    )

    saved = db.get(result.entity_text)

    print(f"Entity saved: {saved is not None}")

    if saved:
        print(f"Canonical name: {saved.canonical_name}")
        print(f"Type: {saved.entity_type}")
        print(f"Research entries: {len(saved.research)}")

    print()
    print("REAL RESEARCH FULL INTEGRATION: PASS")
