from research.research_provider import DuckDuckGoResearchProvider

provider = DuckDuckGoResearchProvider(timeout=20)

results = provider.search(
    '"Oxford University" organization',
    max_results=5,
)

print("=== DUCKDUCKGO PROVIDER TEST ===")
print(f"Result count: {len(results)}")

for i, result in enumerate(results, 1):
    print()
    print(f"[{i}]")
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Source: {result.source}")
    print(f"Relevance: {result.relevance}")
    print(f"Snippet: {result.snippet[:300]}")

if results:
    print()
    print("RESEARCH PROVIDER: PASS")
else:
    print()
    print("RESEARCH PROVIDER: FAIL")
