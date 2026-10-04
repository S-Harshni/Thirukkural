"""Retrieval quality: keyword (BM25) vs dense multilingual (e5) vs hybrid, on three query sets.

- chapter themes: the 133 English chapter titles; a hit is any couplet of that chapter in the top k
- student questions (English): 120 generated questions; a hit is the exact couplet it was written from
- student questions (Hindi): the same questions in Hindi, while the couplets are in Tamil and English, so keyword
  search cannot match words; this is the cross-lingual test
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kuralai.corpus import chapters, load  # noqa: E402
from kuralai.search import Searcher  # noqa: E402


def metrics(ranks: list[int | None]) -> dict:
    n = len(ranks)
    return {"queries": n, "hit@1": round(sum(r == 1 for r in ranks) / n, 3), "hit@5": round(sum(r is not None and r <= 5 for r in ranks) / n, 3),
            "hit@10": round(sum(r is not None and r <= 10 for r in ranks) / n, 3),
            "mrr@10": round(sum(1 / r for r in ranks if r is not None and r <= 10) / n, 3)}


def main() -> None:
    kurals = load()
    s = Searcher(kurals)
    questions = json.loads((ROOT / "data" / "eval_questions.json").read_text(encoding="utf-8"))
    results = {}
    for method in ("bm25", "dense", "hybrid"):
        chapter_ranks = []
        for ch in chapters():
            got = s.search(ch["translation"], method, k=10)
            chapter_ranks.append(next((i + 1 for i, k in enumerate(got) if k.chapter_no == ch["number"]), None))
        results[method] = {"chapter_themes": metrics(chapter_ranks)}
        for lang in ("en", "hi"):
            ranks = []
            for q in questions:
                got = s.search(q[lang], method, k=10)
                ranks.append(next((i + 1 for i, k in enumerate(got) if k.no == q["kural"]), None))
            results[method][f"questions_{lang}"] = metrics(ranks)
        print(method, json.dumps(results[method]), flush=True)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "retrieval.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
