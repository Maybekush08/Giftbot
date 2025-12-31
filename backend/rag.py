from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from .llm import embed_texts
from .models import SearchResult


@dataclass
class RagDoc:
    text: str
    url: str
    title: str


def build_docs(results: List[SearchResult]) -> List[RagDoc]:
    docs: List[RagDoc] = []
    for r in results:
        txt = f"TITLE: {r.title}\nURL: {r.url}\nSNIPPET: {r.snippet}"
        docs.append(RagDoc(text=txt, url=r.url, title=r.title))
    return docs


def top_k_by_similarity(query_text: str, docs: List[RagDoc], k: int = 12) -> List[RagDoc]:
    if not docs:
        return []

    q_emb = embed_texts([query_text])[0]
    d_embs = embed_texts([d.text for d in docs])

    q = np.array(q_emb, dtype=np.float32)
    D = np.array(d_embs, dtype=np.float32)

    q = q / (np.linalg.norm(q) + 1e-9)
    D = D / (np.linalg.norm(D, axis=1, keepdims=True) + 1e-9)

    sims = D @ q
    idx = np.argsort(-sims)[:k]
    return [docs[i] for i in idx]
