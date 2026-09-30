from dataclasses import dataclass, field
from time import sleep
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


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


class DuckDuckGoResearchProvider(ResearchProvider):
    """
    Provider web gratis berbasis halaman hasil DuckDuckGo.

    Menggunakan dua endpoint:
    1. DuckDuckGo HTML
    2. DuckDuckGo Lite sebagai fallback

    Provider melakukan retry sederhana untuk mengatasi gangguan sementara,
    rate limit, atau kegagalan koneksi.

    Jika seluruh endpoint gagal, search() mengembalikan [] sehingga
    AdaptiveResearchEngine tetap dapat menangani kegagalan research
    secara normal.
    """

    HTML_SEARCH_URL = "https://html.duckduckgo.com/html/"
    LITE_SEARCH_URL = "https://lite.duckduckgo.com/lite/"

    # Backward compatibility dengan kode yang mungkin masih membaca
    # SEARCH_URL.
    SEARCH_URL = HTML_SEARCH_URL

    def __init__(
        self,
        timeout=20,
        max_retries=2,
        retry_delay=1.5,
        user_agent=(
            "Mozilla/5.0 (Linux; Android 10; Mobile) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0 Mobile Safari/537.36"
        ),
        session=None,
    ):
        if timeout <= 0:
            raise ValueError("timeout harus lebih besar dari 0.")

        if max_retries < 0:
            raise ValueError("max_retries tidak boleh negatif.")

        if retry_delay < 0:
            raise ValueError("retry_delay tidak boleh negatif.")

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.session = session or requests.Session()

        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/xhtml+xml;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )

    def search(self, query, max_results=5):
        if not isinstance(query, str) or not query.strip():
            return []

        if max_results <= 0:
            return []

        query = query.strip()

        # Endpoint utama terlebih dahulu.
        endpoints = [
            (
                self.HTML_SEARCH_URL,
                self._parse_results,
            ),
            (
                self.LITE_SEARCH_URL,
                self._parse_lite_results,
            ),
        ]

        for endpoint, parser in endpoints:
            html = self._request_with_retry(
                endpoint=endpoint,
                query=query,
            )

            if html is None:
                continue

            try:
                results = parser(
                    html=html,
                    max_results=max_results,
                )
            except Exception:
                results = []

            if results:
                return results

        return []

    def _request_with_retry(self, endpoint, query):
        """
        Jalankan request dengan retry.

        Return:
            str | None
        """
        total_attempts = self.max_retries + 1

        for attempt in range(total_attempts):
            try:
                response = self.session.get(
                    endpoint,
                    params={"q": query},
                    timeout=self.timeout,
                    allow_redirects=True,
                )

                # Status HTTP yang mengindikasikan kemungkinan gangguan
                # sementara akan dicoba lagi.
                if response.status_code in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }:
                    if attempt < total_attempts - 1:
                        self._sleep_before_retry(attempt)
                        continue

                    return None

                response.raise_for_status()

                # Pastikan server benar-benar memberikan HTML.
                if not response.text:
                    if attempt < total_attempts - 1:
                        self._sleep_before_retry(attempt)
                        continue

                    return None

                return response.text

            except requests.RequestException:
                if attempt < total_attempts - 1:
                    self._sleep_before_retry(attempt)
                    continue

                return None

        return None

    def _sleep_before_retry(self, attempt):
        if self.retry_delay <= 0:
            return

        # 1x, 2x, 4x, ... untuk mengurangi tekanan pada endpoint.
        delay = self.retry_delay * (2 ** attempt)
        sleep(delay)

    @classmethod
    def _parse_results(cls, html, max_results):
        soup = BeautifulSoup(html, "html.parser")
        results = []

        for result_block in soup.select(".result"):
            title_element = result_block.select_one(
                ".result__title a"
            )

            if title_element is None:
                continue

            title = title_element.get_text(
                " ",
                strip=True,
            )

            href = title_element.get(
                "href",
                "",
            ).strip()

            if not title or not href:
                continue

            url = cls._extract_result_url(href)

            if not url:
                continue

            snippet_element = result_block.select_one(
                ".result__snippet"
            )

            snippet = (
                snippet_element.get_text(
                    " ",
                    strip=True,
                )
                if snippet_element is not None
                else ""
            )

            results.append(
                ResearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo",
                    relevance=0.0,
                    metadata={
                        "provider": "DuckDuckGoResearchProvider",
                        "endpoint": "html",
                    },
                )
            )

            if len(results) >= max_results:
                break

        return results

    @classmethod
    def _parse_lite_results(cls, html, max_results):
        """
        Parser untuk DuckDuckGo Lite.

        Struktur Lite berbeda dari endpoint HTML biasa.
        """

        soup = BeautifulSoup(html, "html.parser")
        results = []

        # DDG Lite biasanya menggunakan class result-link.
        links = soup.select("a.result-link")

        for link in links:
            title = link.get_text(
                " ",
                strip=True,
            )

            href = link.get(
                "href",
                "",
            ).strip()

            if not title or not href:
                continue

            url = cls._extract_result_url(href)

            if not url:
                continue

            # Pada Lite, snippet biasanya berada pada elemen
            # result-snippet atau td.result-snippet.
            parent = link.parent
            container = parent.parent if parent is not None else None

            snippet = ""

            if container is not None:
                snippet_element = container.select_one(
                    ".result-snippet"
                )

                if snippet_element is not None:
                    snippet = snippet_element.get_text(
                        " ",
                        strip=True,
                    )

            results.append(
                ResearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source="duckduckgo",
                    relevance=0.0,
                    metadata={
                        "provider": "DuckDuckGoResearchProvider",
                        "endpoint": "lite",
                    },
                )
            )

            if len(results) >= max_results:
                break

        return results

    @staticmethod
    def _extract_result_url(href):
        """
        DuckDuckGo kadang memberikan URL langsung dan kadang
        memberikan URL redirect.

        Ambil URL tujuan jika parameter uddg tersedia.
        """

        if not href:
            return ""

        if href.startswith("//"):
            href = "https:" + href

        if href.startswith("/"):
            href = urljoin(
                DuckDuckGoResearchProvider.SEARCH_URL,
                href,
            )

        if "uddg=" in href:
            try:
                parsed = urlparse(href)

                target = parse_qs(
                    parsed.query
                ).get(
                    "uddg",
                    [None],
                )[0]

                if target:
                    return target

            except Exception:
                pass

        return href
