"""Tutor quality: does the grounded answer cite the right couplet, stay in the asked language and decline
unrelated questions? Zero-shot vs few-shot prompts on Qwen 2.5 3B, dense multilingual retrieval (top 3) for context."""
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kuralai.corpus import load  # noqa: E402
from kuralai.llm import ChatModel  # noqa: E402
from kuralai.search import Searcher  # noqa: E402
from kuralai.tutor import answer  # noqa: E402

CONFIGS = [("zero_shot", "qwen2.5:3b"), ("few_shot", "qwen2.5:3b")]


def main() -> None:
    kurals = load()
    by_no = {k.no: k for k in kurals}
    s = Searcher(kurals)
    questions = json.loads((ROOT / "data" / "eval_questions.json").read_text(encoding="utf-8"))[:40]
    off = json.loads((ROOT / "data" / "off_topic_questions.json").read_text(encoding="utf-8"))
    items = [(q[lang], lang, q["kural"]) for q in questions for lang in ("en", "hi")] + [(o["q"], o["lang"], None) for o in off]
    contexts = {(text, lang): s.search(text, "dense", k=3) for text, lang, _ in items}
    cache = ROOT / "out" / "kuralai" / "llm_cache.jsonl"
    results, examples = {}, []
    for variant, model in CONFIGS:
        llm = ChatModel(model, cache=cache)
        rows = []
        for text, lang, target in items:
            ctx = contexts[(text, lang)]
            a = answer(llm, text, ctx, lang, variant, examples_ctx=by_no, seed=7)
            rows.append({"q": text, "lang": lang, "target": target, "retrieved": [k.no for k in ctx], "answer": a.answer,
                         "cited": a.cited, "declined": a.declined, "json_ok": a.json_ok, "cited_valid": a.cited_valid,
                         "lang_ok": a.lang_ok, "ms": a.ms})
        on = [r for r in rows if r["target"] is not None]
        reachable = [r for r in on if r["target"] in r["retrieved"]]
        offt = [r for r in rows if r["target"] is None]
        name = f"{variant}:{model}"
        results[name] = {
            "questions": len(on), "off_topic": len(offt),
            "cites_target": round(statistics.mean(r["target"] in r["cited"] for r in on), 3),
            "cites_target_when_retrieved": round(statistics.mean(r["target"] in r["cited"] for r in reachable), 3),
            "answered_not_declined": round(statistics.mean(not r["declined"] for r in on), 3),
            "declined_off_topic": round(statistics.mean(r["declined"] for r in offt), 3),
            "citations_valid": round(statistics.mean(r["cited_valid"] for r in rows), 3),
            "language_ok": round(statistics.mean(r["lang_ok"] for r in rows if r["answer"]), 3),
            "json_ok": round(statistics.mean(r["json_ok"] for r in rows), 3),
            "latency_p50_ms": round(statistics.median(r["ms"] for r in rows)),
        }
        print(name, json.dumps(results[name]), flush=True)
        examples += [{"config": name, **r} for r in rows]
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "tutor.json").write_text(json.dumps({"summary": results, "rows": examples}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
