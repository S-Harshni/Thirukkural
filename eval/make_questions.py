"""Build the evaluation question set (run once; the output is committed as data/eval_questions.json).

For 120 couplets sampled across all 133 chapters, a local LLM (llama3.2:3b) writes the question a student might ask whose
answer is that couplet's idea (without quoting it). The couplet it was written from is the expected answer, so retrieval
and citations can be scored automatically. The Hindi versions (data/eval_questions_hi.json) were translated separately,
not by the models under test: the 3B models' own Hindi translations were too poor to use as a test set.
"""
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kuralai.corpus import load  # noqa: E402
from kuralai.llm import ChatModel  # noqa: E402

ASK = """Here is the idea of one couplet of the Thirukkural:
"{idea}"
Write ONE short question (at most 14 words) that a student might ask, whose answer is this idea.
Do not quote the couplet and do not mention couplet numbers. Output only the question."""


def clean(text: str) -> str:
    text = text.strip().splitlines()[0].strip().strip('"').strip()
    return re.sub(r"^(question|प्रश्न)\s*:\s*", "", text, flags=re.I)


def main() -> None:
    kurals = load()
    rng = random.Random(7)
    by_chapter = {}
    for k in kurals:
        by_chapter.setdefault(k.chapter_no, []).append(k)
    picked = [rng.choice(v) for v in by_chapter.values()]
    picked = sorted(rng.sample(picked, 120), key=lambda k: k.no)
    cache = ROOT / "out" / "kuralai" / "llm_cache.jsonl"
    writer = ChatModel("llama3.2:3b", cache=cache)
    hindi_path = ROOT / "data" / "eval_questions_hi.json"
    hindi = {int(k): v for k, v in json.loads(hindi_path.read_text(encoding="utf-8")).items()} if hindi_path.exists() else {}
    rows = []
    for k in picked:
        q_en, _ = writer.chat([{"role": "user", "content": ASK.format(idea=k.english)}], temperature=0.4, seed=k.no, max_tokens=40)
        q_en = clean(q_en)
        rows.append({"kural": k.no, "chapter": k.chapter_no, "en": q_en, "hi": hindi.get(k.no, "")})
        print(k.no, "|", q_en, flush=True)
    (ROOT / "data" / "eval_questions.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
