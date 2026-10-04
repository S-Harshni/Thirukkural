"""Write the results tables into README.md (between the <!-- results --> markers) from results/*.json."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
pct = lambda v: "–" if v is None else f"{v * 100:.1f}%"  # noqa: E731
METHODS = {"bm25": "Keywords (BM25)", "dense": "Dense multilingual (e5-small)", "hybrid": "Hybrid (rank fusion)"}


def table(header, rows) -> str:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" if i == 0 else "---:" for i in range(len(header))) + "|"]
    return "\n".join(out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main() -> None:
    r = json.loads((RES / "retrieval.json").read_text())
    parts = ["### Finding the right couplet (hit@5 / MRR@10)\n", table(
        ["Search", "Chapter themes (133)", "Student questions, English (120)", "Student questions, Hindi (120)"],
        [[METHODS[m]] + [f"{pct(r[m][k]['hit@5'])} / {r[m][k]['mrr@10']:.3f}" for k in ("chapter_themes", "questions_en", "questions_hi")] for m in METHODS])]
    t = json.loads((RES / "tutor.json").read_text())["summary"]
    parts += ["\n### Grounded tutor (40 questions asked in English and in Hindi + 30 off-topic)\n", table(
        ["Prompt · model", "Cites the right couplet", "…when it was retrieved", "Declines off-topic", "Citations valid", "Right language", "Valid JSON", "p50 ms"],
        [[k.replace("zero_shot", "Zero-shot").replace("few_shot", "Few-shot").replace(":", " · "), pct(v["cites_target"]), pct(v["cites_target_when_retrieved"]),
          pct(v["declined_off_topic"]), pct(v["citations_valid"]), pct(v["language_ok"]), pct(v["json_ok"]), f"{v['latency_p50_ms']:,}"] for k, v in t.items()])]
    if (RES / "voice.json").exists():
        v = json.loads((RES / "voice.json").read_text())["summary"]
        parts += ["\n### Spoken questions (Whisper small, CPU)\n", table(
            ["Language", "Typed: right couplet in top 5", "Spoken: right couplet in top 5", "Language detected"],
            [[{"en": "English", "hi": "Hindi"}[lang], pct(v[lang]["typed_hit@5"]), pct(v[lang]["spoken_hit@5"]), pct(v[lang]["language_detected_ok"])] for lang in ("en", "hi")]),
            f"\nMedian Whisper time per question: {v['stt_seconds_median']} s."]
    readme = (ROOT / "README.md").read_text()
    readme = re.sub(r"<!-- results -->.*<!-- /results -->", "<!-- results -->\n" + "\n".join(parts) + "\n<!-- /results -->", readme, flags=re.S)
    (ROOT / "README.md").write_text(readme)
    print("README tables updated")


if __name__ == "__main__":
    main()
