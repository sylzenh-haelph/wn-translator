from dataclasses import dataclass, field
from time import sleep

import requests


@dataclass
class ResearchResult:
    title: str
    url: str
    snippet: str = ""
    source: str = ""
    relevance: float = 0.0
    metadata: dict = field(default_factory=dict)


class ResearchProvider:
    def search(self, query, max_results=5):
        raise NotImplementedError


class MockResearchProvider(ResearchProvider):
    def __init__(self, results=None):
        self.results = results or []

    def search(self, query, max_results=5):
        return self.results[:max_results]


class TavilyResearchProvider(ResearchProvider):
    """Web search provider menggunakan Tavily Search API."""

    SEARCH_URL = "https://api.tavily.com/search"

    def __init__(
        self,
        api_key=None,
        timeout=20,
        max_retries=1,
        retry_delay=1.0,
        session=None,
    ):
        import os

        if timeout <= 0:
            raise ValueError("timeout harus lebih besar dari 0.")
        if max_retries < 0:
            raise ValueError("max_retries tidak boleh negatif.")
        if retry_delay < 0:
            raise ValueError("retry_delay tidak boleh negatif.")

        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY belum tersedia.")

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = session or requests.Session()

    def search(self, query, max_results=5):
        if not isinstance(query, str) or not query.strip():
            return []
        if max_results <= 0:
            return []

        payload = {
            "query": query.strip(),
            "max_results": min(int(max_results), 20),
            "search_depth": "basic",
            "include_answer": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    self.SEARCH_URL,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                if not isinstance(data, dict):
                    return []

                results = []
                for item in data.get("results", []):
                    if not isinstance(item, dict):
                        continue

                    title = str(item.get("title") or "").strip()
                    url = str(item.get("url") or "").strip()
                    if not title or not url:
                        continue

                    try:
                        score = float(item.get("score") or 0.0)
                    except (TypeError, ValueError):
                        score = 0.0

                    results.append(
                        ResearchResult(
                            title=title,
                            url=url,
                            snippet=str(item.get("content") or "").strip(),
                            source="tavily",
                            relevance=score,
                            metadata={
                                "provider": "TavilyResearchProvider",
                            },
                        )
                    )
                    if len(results) >= max_results:
                        break

                return results

            except (requests.RequestException, ValueError):
                if attempt >= self.max_retries:
                    return []
                if self.retry_delay:
                    sleep(self.retry_delay * (2 ** attempt))

        return []
