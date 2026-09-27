from dataclasses import dataclass, field

from research.query_builder import build_adaptive_query
from research.research_evaluator import evaluate_research


@dataclass
class ResearchEvidence:
    title: str
    url: str
    snippet: str
    source: str


@dataclass
class AdaptiveResearchResult:
    success: bool
    entity_text: str
    entity_type: str
    final_query: str
    confidence: float
    evidence: list[ResearchEvidence] = field(
        default_factory=list
    )
    attempts: int = 0
    reason: str = ""
    research_failed: bool = False


class AdaptiveResearchEngine:
    def __init__(
        self,
        provider,
        client,
        max_attempts=4,
    ):
        self.provider = provider
        self.client = client
        self.max_attempts = max_attempts

    def research(
        self,
        entity_text,
        entity_type,
        novel_title=None,
        author=None,
        chapter_context=None,
    ):
        last_query = ""

        for attempt in range(1, self.max_attempts + 1):
            query = build_adaptive_query(
                entity_text=entity_text,
                entity_type=entity_type,
                novel_title=novel_title,
                author=author,
                chapter_context=chapter_context,
                attempt=attempt,
            )

            last_query = query

            results = self.provider.search(
                query,
                max_results=5,
            )

            evaluation = evaluate_research(
                client=self.client,
                entity_text=entity_text,
                entity_type=entity_type,
                query=query,
                results=results,
            )

            if evaluation.sufficient:
                evidence = []

                for index in evaluation.selected_indices:
                    result = results[index]

                    evidence.append(
                        ResearchEvidence(
                            title=result.title,
                            url=result.url,
                            snippet=result.snippet,
                            source=result.source,
                        )
                    )

                return AdaptiveResearchResult(
                    success=True,
                    entity_text=entity_text,
                    entity_type=entity_type,
                    final_query=query,
                    confidence=evaluation.confidence,
                    evidence=evidence,
                    attempts=attempt,
                    reason=evaluation.reason,
                    research_failed=False,
                )

        return AdaptiveResearchResult(
            success=False,
            entity_text=entity_text,
            entity_type=entity_type,
            final_query=last_query,
            confidence=0.0,
            evidence=[],
            attempts=self.max_attempts,
            reason=(
                "Research did not produce sufficient evidence "
                "within the maximum number of attempts."
            ),
            research_failed=True,
        )
