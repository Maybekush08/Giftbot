from typing import List, Set
from urllib.parse import urlparse
import re
import numpy as np

from .models import GiftProfile, SearchResult, GiftIdea, GiftBatch
from .prompts import SYSTEM_GIFT_BOT, QUERY_PLANNER, IDEA_EXTRACTOR, BUY_LINK_FINDER, CARD_WRITER
from .search_providers import search_web
from .rag import build_docs, top_k_by_similarity
from .llm import llm_json, llm_text, embed_texts
from .config import PINTEREST_WEIGHT, ETSY_WEIGHT, DEFAULT_WEIGHT, RETAIL_WEIGHT, BUY_LINKS_PER_IDEA


RETAIL_DOMAINS = {
    "amazon.com", "target.com", "walmart.com", "bestbuy.com", "nike.com", "adidas.com",
    "crateandbarrel.com", "potterybarn.com", "sephora.com", "ulta.com", "barnesandnoble.com",
    "etsy.com"
}


def _domain_weight(url: str) -> float:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return DEFAULT_WEIGHT

    if "pinterest." in host:
        return PINTEREST_WEIGHT
    if host.endswith("etsy.com"):
        return ETSY_WEIGHT
    if any(host.endswith(d) for d in RETAIL_DOMAINS):
        return RETAIL_WEIGHT
    return DEFAULT_WEIGHT


def _rating_signal(text: str) -> float:
    """
    Lightweight extraction from snippets only.
    If no rating text is present, returns 0.
    """
    t = (text or "").lower()
    m = re.search(r"(\d\.\d)\s*(?:out of\s*5|stars?)", t)
    if m:
        try:
            return float(m.group(1)) / 5.0
        except Exception:
            return 0.0
    return 0.0


def _profile_text(p: GiftProfile) -> str:
    parts = [
        f"recipient: {p.recipient}" if p.recipient else "",
        f"age: {p.age}" if p.age else "",
        f"relationship: {p.relationship}" if p.relationship else "",
        f"personality: {p.personality}" if p.personality else "",
        f"interests: {p.interests}" if p.interests else "",
        f"occasion: {p.occasion}" if p.occasion else "",
        f"budget_usd: {p.budget_usd}" if p.budget_usd else "",
        f"no_go: {p.no_go}" if p.no_go else "",
        f"extra_notes: {p.extra_notes}" if p.extra_notes else "",
    ]
    return "\n".join([x for x in parts if x]).strip()


def plan_queries(profile: GiftProfile) -> List[str]:
    user = f"PROFILE:\n{_profile_text(profile)}\n\nReturn JSON with key 'queries' as an array."
    raw = llm_json(SYSTEM_GIFT_BOT, f"{QUERY_PLANNER}\n\n{user}")
    # Minimal parsing to avoid brittle strict schemas
    import json
    obj = json.loads(raw)
    queries = obj.get("queries") or []
    return [q for q in queries if isinstance(q, str) and q.strip()][:6]


def gather_results(queries: List[str]) -> List[SearchResult]:
    seen = set()
    all_results: List[SearchResult] = []
    for q in queries:
        for r in search_web(q):
            if r.url in seen:
                continue
            seen.add(r.url)
            all_results.append(r)
    return all_results


def extract_ideas(profile: GiftProfile, results: List[SearchResult], k: int, exclude_names: Set[str]) -> List[GiftIdea]:
    import json

    profile_txt = _profile_text(profile)
    condensed = []
    for r in results[:40]:
        condensed.append(f"- {r.title}\n  {r.url}\n  {r.snippet}")
    snippets = "\n".join(condensed)

    exclude_txt = "\n".join(sorted(exclude_names)) if exclude_names else "(none)"

    user = f"""
PROFILE:
{profile_txt}

EXCLUDE IDEAS (do not repeat):
{exclude_txt}

WEB SNIPPETS:
{snippets}

Return JSON with key 'ideas' as array of objects:
name (string), why_it_fits (string), estimated_price (string|null), evidence_urls (array of strings).
"""

    raw = llm_json(SYSTEM_GIFT_BOT, IDEA_EXTRACTOR.format(k=k) + "\n\n" + user)
    obj = json.loads(raw)

    ideas = []
    for it in (obj.get("ideas") or []):
        try:
            name = (it.get("name") or "").strip()
            if not name:
                continue
            if name.lower() in {x.lower() for x in exclude_names}:
                continue
            ideas.append(
                GiftIdea(
                    name=name,
                    why_it_fits=(it.get("why_it_fits") or "").strip(),
                    estimated_price=it.get("estimated_price"),
                    buy_link=None,
                    score=0.0,
                    evidence_urls=[u for u in (it.get("evidence_urls") or []) if isinstance(u, str)],
                )
            )
        except Exception:
            continue

    return ideas[:k]


def _fit_scores(profile: GiftProfile, ideas: List[GiftIdea]) -> List[float]:
    if not ideas:
        return []

    profile_txt = _profile_text(profile)
    texts = [profile_txt] + [f"{g.name}\n{g.why_it_fits}" for g in ideas]
    embs = embed_texts(texts)

    p = np.array(embs[0], dtype=np.float32)
    p = p / (np.linalg.norm(p) + 1e-9)

    out = []
    for e in embs[1:]:
        v = np.array(e, dtype=np.float32)
        v = v / (np.linalg.norm(v) + 1e-9)
        out.append(float(v @ p))
    return out


def find_buy_link(idea: GiftIdea) -> str | None:
    import json

    evidence_urls = idea.evidence_urls or []
    evidence_hint = ""
    if any("etsy.com" in u for u in evidence_urls):
        evidence_hint = "If an Etsy listing URL is present in evidence, prefer that as a buy link."

    raw = llm_json(
        SYSTEM_GIFT_BOT,
        f"{BUY_LINK_FINDER}\n\nIDEA: {idea.name}\n{evidence_hint}\nReturn JSON array of strings.",
    )
    queries = json.loads(raw)
    queries = [q for q in queries if isinstance(q, str) and q.strip()]

    best = None
    best_w = 0.0

    for q in queries[:5]:
        results = search_web(q)
        for r in results[:BUY_LINKS_PER_IDEA]:
            w = _domain_weight(r.url)
            if w > best_w:
                best_w = w
                best = r.url

    if best:
        return best

    if evidence_urls:
        return evidence_urls[0]
    return None


def rank_and_fill(profile: GiftProfile, ideas: List[GiftIdea], backing_results: List[SearchResult]) -> List[GiftIdea]:
    fit = _fit_scores(profile, ideas)

    # Build quick evidence text for ratings/domain scoring
    url_to_text = {}
    for r in backing_results:
        url_to_text[r.url] = f"{r.title}\n{r.snippet}"

    for i, g in enumerate(ideas):
        domain_boost = 0.0
        rating_boost = 0.0

        for u in (g.evidence_urls or [])[:4]:
            domain_boost = max(domain_boost, _domain_weight(u))
            rating_boost = max(rating_boost, _rating_signal(url_to_text.get(u, "")))

        fit_score = (fit[i] + 1.0) / 2.0  # normalize cosine from [-1,1] to [0,1]
        domain_score = min(domain_boost / 1.35, 1.0) if domain_boost else 0.0

        g.score = 0.55 * fit_score + 0.25 * domain_score + 0.20 * rating_boost

    ideas.sort(key=lambda x: x.score, reverse=True)
    return ideas


def generate_batch(profile: GiftProfile, exclude_names: Set[str], k: int = 5) -> GiftBatch:
    queries = plan_queries(profile)
    results = gather_results(queries)

    # RAG selection: pick top documents most relevant to profile
    docs = build_docs(results)
    top_docs = top_k_by_similarity(_profile_text(profile), docs, k=18)

    # Rebuild a reduced result list from top docs only
    top_urls = {d.url for d in top_docs}
    reduced = [r for r in results if r.url in top_urls]

    ideas = extract_ideas(profile, reduced, k=k, exclude_names=exclude_names)
    ideas = rank_and_fill(profile, ideas, reduced)

    # Fill buy links
    for g in ideas[:k]:
        g.buy_link = find_buy_link(g)

    # Keep final top k
    final = ideas[:k]
    notes = f"Search queries used:\n" + "\n".join(f"- {q}" for q in queries)
    return GiftBatch(ideas=final, search_notes=notes)


def generate_cards(profile: GiftProfile, selected_ideas: List[GiftIdea]) -> str:
    idea_lines = "\n".join([f"- {g.name}" for g in selected_ideas])
    user = f"PROFILE:\n{_profile_text(profile)}\n\nSELECTED IDEAS:\n{idea_lines}\n\n{CARD_WRITER}"
    return llm_text(SYSTEM_GIFT_BOT, user)
