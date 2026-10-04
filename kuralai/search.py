"""Keyword (BM25), dense multilingual (e5) and hybrid (reciprocal rank fusion) search over the couplets."""
from pathlib import Path

import numpy as np

from .bm25 import BM25
from .corpus import Kural

CACHE = Path(__file__).resolve().parents[1] / "out" / "kuralai"
DENSE_MODEL = "intfloat/multilingual-e5-small"  # 100+ languages incl. Tamil and Hindi, 118M parameters


class Searcher:
    def __init__(self, kurals: list[Kural], dense: bool = True):
        self.kurals = kurals
        self.bm25 = BM25([k.passage(with_chapter=False) for k in kurals])
        self.model = self.vectors = None
        if dense:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(DENSE_MODEL, device="cpu")
            path = CACHE / "e5_passages.npy"
            if path.exists():
                self.vectors = np.load(path)
            else:
                self.vectors = self.model.encode([f"passage: {k.passage(with_chapter=False)}" for k in kurals], batch_size=32,
                                                 normalize_embeddings=True, show_progress_bar=True)
                CACHE.mkdir(parents=True, exist_ok=True)
                np.save(path, self.vectors)

    def _rank(self, scores) -> list[int]:
        return list(np.argsort(-np.asarray(scores), kind="stable"))

    def search(self, query: str, method: str = "hybrid", k: int = 5) -> list[Kural]:
        if method == "bm25":
            order = self._rank(self.bm25.scores(query))
        elif method == "dense":
            q = self.model.encode([f"query: {query}"], normalize_embeddings=True)[0]
            order = self._rank(self.vectors @ q)
        else:  # reciprocal rank fusion of the two lists
            fused = np.zeros(len(self.kurals))
            for m in ("bm25", "dense"):
                for rank, i in enumerate(self._rank(self.bm25.scores(query) if m == "bm25" else
                                                    self.vectors @ self.model.encode([f"query: {query}"], normalize_embeddings=True)[0])[:100]):
                    fused[i] += 1 / (60 + rank)
            order = self._rank(fused)
        return [self.kurals[i] for i in order[:k]]
