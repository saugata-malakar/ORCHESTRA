"""
retriever.py — BM25Okapi-based corpus retriever.

No network calls; indexes the in-memory document list at startup.
Supports optional company-affinity boosting for more precise routing.
"""

import re
from typing import List, Dict, Optional

from rank_bm25 import BM25Okapi

from config import TOP_K_DOCS


# ── Stopwords (lightweight) ───────────────────────────────────────────────────
_STOPWORDS = frozenset({
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "they",
    "it", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "can", "the", "a", "an", "and", "or", "but",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "up",
    "out", "about", "into", "that", "this", "these", "those", "not",
    "no", "so", "if", "as", "when", "what", "how", "why", "who",
    "which", "then", "than", "also", "just", "very", "more", "some",
    "please", "help", "need", "want", "like", "get", "hi", "hello",
    "thanks", "thank",
})

# Company-name affinity boost multiplier
_COMPANY_BOOST = 1.4


class BM25Retriever:
    """
    Wraps BM25Okapi to provide:
      - tokenise with stopword removal
      - optional company-affinity boosting
      - deduplication by (source, chunk_idx)
    """

    def __init__(self, documents: List[Dict]):
        self.documents = documents
        if not documents:
            self.bm25 = None
            return
        self._tokenized = [_tokenize(doc["text"]) for doc in documents]
        self.bm25 = BM25Okapi(self._tokenized)

    # ── Public ────────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        company: Optional[str] = None,
        top_k: int = TOP_K_DOCS,
    ) -> List[Dict]:
        """
        Return up to `top_k` deduplicated document chunks ranked by BM25 score.
        `company` can be 'HackerRank', 'Claude', 'Visa', or None/empty.
        """
        query_tokens = _tokenize(query)
        if not query_tokens or self.bm25 is None:
            return []

        raw_scores = self.bm25.get_scores(query_tokens)

        scored: list = []
        for idx, score in enumerate(raw_scores):
            if score <= 0:
                continue
            # Company-affinity boost
            if company and self.documents[idx]["company"].lower() == company.lower():
                score *= _COMPANY_BOOST
            scored.append((idx, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Deduplicate by (source, chunk_idx)
        seen: set = set()
        results: List[Dict] = []
        for idx, score in scored:
            doc = self.documents[idx]
            key = (doc["source"], doc["chunk_idx"])
            if key in seen:
                continue
            seen.add(key)
            results.append({**doc, "bm25_score": round(score, 4)})
            if len(results) >= top_k:
                break

        return results


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    tokens = re.findall(r"\b[a-z0-9][a-z0-9']*\b", text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]
