from translation.model_client import GeminiClient
from research.research_provider import DuckDuckGoResearchProvider
from research.query_builder import build_adaptive_query
from research.research_evaluator import evaluate_research


entity_text = "Oxford University"
entity_type = "organization"
novel_title = "Research Integration Test"
author = "Test Author"
chapter_context = (
    "The character studied at Oxford University before "
    "returning to the kingdom."
)

provider = DuckDuckGoResearchProvider(timeout=20)
client = GeminiClient(model="gemini-3.5-flash-lite")

for attempt in range(1, 4):
    query = build_adaptive_query(
        entity_text=entity_text,
        entity_type=entity_type,
        novel_title=novel_title,
        author=author,
        chapter_context=chapter_context,
        attempt=attempt,
    )

    results = provider.search(query, max_results=5)

    print()
    print(f"=== ATTEMPT {attempt} ===")
    print(f"Query: {query}")
    print(f"Result count: {len(results)}")

    for i, result in enumerate(results):
        print(
            f"{i}: {result.title} | "
            f"{result.url}"
        )

    evaluation = evaluate_research(
        client=client,
        entity_text=entity_text,
        entity_type=entity_type,
        query=query,
        results=results,
    )

    print()
    print(f"Sufficient: {evaluation.sufficient}")
    print(f"Confidence: {evaluation.confidence}")
    print(f"Selected indices: {evaluation.selected_indices}")
    print(f"Needs more context: {evaluation.needs_more_context}")
    print(f"Reason: {evaluation.reason}")

    if evaluation.sufficient:
        print()
        print("ADAPTIVE STEP: PASS")
        break
else:
    print()
    print("ADAPTIVE STEP: FAIL")
