from research.research_provider import (
    MockResearchProvider,
    ResearchResult,
)
from research.research_evaluator import evaluate_research
from translation.model_client import GeminiClient


provider = MockResearchProvider(
    results=[
        ResearchResult(
            title="Royal Palace - Example Novel Wiki",
            url="https://example.com/royal-palace",
            snippet=(
                "The Royal Palace is the main royal residence "
                "in Example Novel."
            ),
            source="example.com",
        ),
        ResearchResult(
            title="Royal Palace Architecture",
            url="https://example.org/palace",
            snippet=(
                "Royal palaces are residences used by monarchs."
            ),
            source="example.org",
        ),
    ]
)

results = provider.search(
    '"Royal Palace" place "Example Novel"',
)

client = GeminiClient()

evaluation = evaluate_research(
    client=client,
    entity_text="Royal Palace",
    entity_type="place",
    query='"Royal Palace" place "Example Novel"',
    results=results,
)

print("=== RESEARCH EVALUATION ===")
print("Sufficient       :", evaluation.sufficient)
print("Confidence       :", evaluation.confidence)
print("Selected indices :", evaluation.selected_indices)
print("Needs more       :", evaluation.needs_more_context)
print("Reason           :", evaluation.reason)
