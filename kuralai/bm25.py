"""BM25 keyword search written from scratch (works on English, Tamil and Devanagari tokens)."""
import math
import re
from collections import Counter

TOKEN = re.compile(r"[a-z0-9]+|[஀-௿]+|[ऀ-ॿ]+")
STOP = set("a an the of to in on and or is are was be by for with as at that this it its from his her he she they them "
           "their who whom which what when where how does do did not no one ones".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(c.values()) for c in self.docs]
        self.avg = sum(self.lens) / len(self.lens)
        df = Counter(t for c in self.docs for t in c)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for c, length in zip(self.docs, self.lens, strict=True):
            s = 0.0
            for t in q:
                tf = c.get(t)
                if tf:
                    s += self.idf[t] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / self.avg))
            out.append(s)
        return out
