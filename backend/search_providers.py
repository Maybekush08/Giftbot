from typing import List
from .models import SearchResult
from .config import TAVILY_API_KEY, MAX_RESULTS_PER_QUERY
import re


def _clean_snippet(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s[:500]


def search_web(query: str) -> List[SearchResult]:
    """
    Uses Tavily when key exists, otherwise falls back to DuckDuckGo.
    Pinterest/Etsy pages are not fetched. Only search results are used.
    """
    if TAVILY_API_KEY:
        return _search_tavily(query)
    return _search_duckduckgo(query)


def _search_tavily(query: str) -> List[SearchResult]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=TAVILY_API_KEY)
    res = client.search(
        query=query,
        search_depth="basic",
        max_results=MAX_RESULTS_PER_QUERY,
        include_answer=False,
        include_raw_content=False,
    )

    out: List[SearchResult] = []
    for r in (res.get("results") or []):
        out.append(
            SearchResult(
                title=r.get("title") or "Untitled",
                url=r.get("url") or "",
                snippet=_clean_snippet(r.get("content") or ""),
                source="tavily",
            )
        )
    return [x for x in out if x.url]


def _search_duckduckgo(query: str) -> List[SearchResult]:
    from duckduckgo_search import DDGS

    out: List[SearchResult] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=MAX_RESULTS_PER_QUERY):
            out.append(
                SearchResult(
                    title=r.get("title") or "Untitled",
                    url=r.get("href") or "",
                    snippet=_clean_snippet(r.get("body") or ""),
                    source="duckduckgo",
                )
            )
    return [x for x in out if x.url]
