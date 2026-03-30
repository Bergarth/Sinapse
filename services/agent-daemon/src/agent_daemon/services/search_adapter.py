"""Search adapter interface and first real web search implementation."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class SearchSource:
    title: str
    url: str


@dataclass(frozen=True)
class SearchResult:
    query: str
    answer: str
    provider_id: str
    sources: list[SearchSource]


class SearchAdapter:
    provider_id = ""

    def search(self, query: str) -> SearchResult:
        raise NotImplementedError


class DuckDuckGoInstantAnswerAdapter(SearchAdapter):
    provider_id = "duckduckgo"

    def __init__(self, endpoint: str = "https://api.duckduckgo.com/") -> None:
        self._endpoint = endpoint.rstrip("/") + "/"

    def search(self, query: str) -> SearchResult:
        params = urllib.parse.urlencode(
            {
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
                "skip_disambig": "1",
            }
        )
        url = f"{self._endpoint}?{params}"
        request = urllib.request.Request(url=url, method="GET")

        with urllib.request.urlopen(request, timeout=15.0) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))

        answer = str(payload.get("AbstractText", "")).strip()
        sources: list[SearchSource] = []

        abstract_url = str(payload.get("AbstractURL", "")).strip()
        heading = str(payload.get("Heading", "")).strip() or "DuckDuckGo instant answer"
        if abstract_url:
            sources.append(SearchSource(title=heading, url=abstract_url))

        for item in payload.get("RelatedTopics", []):
            if not isinstance(item, dict):
                continue

            nested_topics = item.get("Topics")
            if isinstance(nested_topics, list):
                for nested in nested_topics:
                    source = self._related_topic_to_source(nested)
                    if source:
                        sources.append(source)
                continue

            source = self._related_topic_to_source(item)
            if source:
                sources.append(source)

            if len(sources) >= 5:
                break

        deduped_sources: list[SearchSource] = []
        seen_urls: set[str] = set()
        for source in sources:
            normalized_url = source.url.strip()
            if not normalized_url or normalized_url in seen_urls:
                continue
            seen_urls.add(normalized_url)
            deduped_sources.append(source)
            if len(deduped_sources) >= 5:
                break

        if not answer:
            if deduped_sources:
                answer = "I found relevant web sources. Open the links below for details."
            else:
                answer = (
                    "I couldn't find a clear web result for that query. "
                    "Try adding more specific terms like a date, location, or product name."
                )

        return SearchResult(
            query=query,
            answer=answer,
            provider_id=self.provider_id,
            sources=deduped_sources,
        )

    @staticmethod
    def _related_topic_to_source(item: object) -> SearchSource | None:
        if not isinstance(item, dict):
            return None

        url = str(item.get("FirstURL", "")).strip()
        if not url:
            return None

        title = str(item.get("Text", "")).strip()
        if not title:
            title = "Related result"

        return SearchSource(title=title, url=url)


def create_search_adapter(provider_id: str, endpoint: str) -> SearchAdapter:
    normalized_provider = provider_id.strip().lower()
    if normalized_provider in ("duckduckgo", "duckduckgo-instant-answer"):
        return DuckDuckGoInstantAnswerAdapter(endpoint=endpoint)

    raise ValueError(f"Unsupported search provider '{provider_id}'.")

