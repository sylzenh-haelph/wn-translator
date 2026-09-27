from dataclasses import dataclass, field


@dataclass
class ResearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    relevance: float = 0.0
    metadata: dict = field(default_factory=dict)


class ResearchProvider:
    """
    Interface dasar untuk research engine.

    Provider konkret nantinya bisa menggunakan:
    - web search
    - API search
    - sumber lain

    Pipeline utama tidak perlu mengetahui detail
    bagaimana pencarian dilakukan.
    """

    def search(self, query, max_results=5):
        raise NotImplementedError


class MockResearchProvider(ResearchProvider):
    """
    Provider untuk testing pipeline tanpa internet.
    """

    def __init__(self, results=None):
        self.results = results or []

    def search(self, query, max_results=5):
        return self.results[:max_results]
