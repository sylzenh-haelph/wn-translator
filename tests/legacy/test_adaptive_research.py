from research.research_provider import (
    ResearchProvider,
    ResearchResult,
)
from research.adaptive_research import AdaptiveResearchEngine
from translation.model_client import GeminiClient


class AdaptiveMockProvider(ResearchProvider):
    def __init__(self):
        self.call_count = 0

    def search(self, query, max_results=5):
        self.call_count += 1

        if self.call_count == 1:
            return [
                ResearchResult(
                    title="Silver Sword",
                    url="https://example.com/general",
                    snippet=(
                        "A silver sword is a type of sword "
                        "with a silver appearance."
                    ),
                    source="example.com",
                )
            ]

        return [
            ResearchResult(
                title="Silver Sword - Example Novel Wiki",
                url="https://example.com/example-novel",
                snippet=(
                    "The Silver Sword is a named weapon "
                    "used by the protagonist in Example Novel."
                ),
                source="example.com",
            )
        ]


def main():
    provider = AdaptiveMockProvider()
    client = GeminiClient()

    engine = AdaptiveResearchEngine(
        provider=provider,
        client=client,
        max_attempts=4,
    )

    result = engine.research(
        entity_text="Silver Sword",
        entity_type="item",
        novel_title="Example Novel",
        author="Example Author",
        chapter_context=(
            "The Silver Sword was lying on the table "
            "after the battle."
        ),
    )

    print("=== ADAPTIVE RESEARCH ===")
    print("Success       :", result.success)
    print("Entity        :", result.entity_text)
    print("Type          :", result.entity_type)
    print("Attempts      :", result.attempts)
    print("Confidence    :", result.confidence)
    print("Final query   :", result.final_query)
    print("Failed        :", result.research_failed)
    print("Reason        :", result.reason)

    print("\nEvidence:")

    for evidence in result.evidence:
        print("-", evidence.title)
        print(" ", evidence.url)
        print(" ", evidence.snippet)


if __name__ == "__main__":
    main()
