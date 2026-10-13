from research.research_provider import TavilyResearchProvider


def main():
    provider = TavilyResearchProvider(timeout=20)

    results = provider.search(
        '"Oxford University" organization',
        max_results=5,
    )

    print("=== TAVILY PROVIDER TEST ===")
    print(f"Result count: {len(results)}")

    for i, result in enumerate(results, 1):
        print()
        print(f"[{i}]")
        print(f"Title: {result.title}")
        print(f"URL: {result.url}")
        print(f"Source: {result.source}")
        print(f"Relevance: {result.relevance}")
        print(f"Snippet: {result.snippet[:300]}")

    print()
    print(
        "RESEARCH PROVIDER: PASS"
        if results
        else "RESEARCH PROVIDER: FAIL"
    )


if __name__ == "__main__":
    main()
