from translation.model_client import GeminiClient
from research.research_provider import DuckDuckGoResearchProvider
from research.research_evaluator import evaluate_research


provider = DuckDuckGoResearchProvider(timeout=20)

results = provider.search(
    '"Oxford University" organization',
    max_results=5,
)

client = GeminiClient(model="gemini-3.5-flash-lite")

evaluation = evaluate_research(
    client=client,
    entity_text="Oxford University",
    entity_type="organization",
    query='"Oxford University" organization',
    results=results,
)

print("=== RESEARCH EVALUATOR TEST ===")
print(f"Sufficient: {evaluation.sufficient}")
print(f"Confidence: {evaluation.confidence}")
print(f"Reason: {evaluation.reason}")
print(f"Selected indices: {evaluation.selected_indices}")
print(f"Needs more context: {evaluation.needs_more_context}")

print()
print("=== RAW EVALUATION OBJECT ===")
print(evaluation)

if evaluation.sufficient and evaluation.confidence > 0:
    print()
    print("RESEARCH EVALUATOR: PASS")
else:
    print()
    print("RESEARCH EVALUATOR: FAIL")
