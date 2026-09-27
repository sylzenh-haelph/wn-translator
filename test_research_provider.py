from research.research_provider import (
    MockResearchProvider,
    ResearchResult,
)


provider = MockResearchProvider(
    results=[
        ResearchResult(
            title="Example Source",
            url="https://example.com",
            snippet="Example research information.",
            source="example.com",
            relevance=0.9,
        ),
        ResearchResult(
            title="Another Source",
            url="https://example.org",
            snippet="Another piece of information.",
            source="example.org",
            relevance=0.7,
        ),
    ]
)


results = provider.search(
    '"Silver Sword" item',
    max_results=5,
)

print("=== RESEARCH PROVIDER TEST ===")

for result in results:
    print("Title     :", result.title)
    print("URL       :", result.url)
    print("Snippet   :", result.snippet)
    print("Source    :", result.source)
    print("Relevance :", result.relevance)
    print()
