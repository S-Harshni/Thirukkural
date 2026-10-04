"""Spoken questions: 24 student questions (12 English, 12 Hindi) are synthesized with gTTS, transcribed by Whisper
and searched; retrieval from the transcript is compared with retrieval from the typed question."""
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kuralai.corpus import load  # noqa: E402
from kuralai.search import Searcher  # noqa: E402


def main() -> None:
    from kuralai.voice import load_audio, speak, transcribe
    kurals = load()
    s = Searcher(kurals)
    qs = json.loads((ROOT / "data" / "eval_questions.json").read_text(encoding="utf-8"))[60:72]
    rows = []
    for q in qs:
        for lang in ("en", "hi"):
            path, _ = speak(q[lang], lang, ROOT / "out" / "kuralai" / "voice")
            samples = load_audio(path)
            t0 = time.perf_counter()
            res = transcribe(samples)
            stt_s = time.perf_counter() - t0
            typed = [k.no for k in s.search(q[lang], "dense", k=5)]
            spoken = [k.no for k in s.search(res["text"], "dense", k=5)]
            rows.append({"kural": q["kural"], "lang": lang, "question": q[lang], "transcript": res["text"],
                         "detected": res["language"], "typed_hit5": q["kural"] in typed, "spoken_hit5": q["kural"] in spoken,
                         "audio_s": round(len(samples) / 16000, 2), "stt_s": round(stt_s, 2)})
            print(lang, rows[-1]["typed_hit5"], rows[-1]["spoken_hit5"], res["text"][:80], flush=True)
    summary = {lang: {"typed_hit@5": round(statistics.mean(r["typed_hit5"] for r in rows if r["lang"] == lang), 3),
                      "spoken_hit@5": round(statistics.mean(r["spoken_hit5"] for r in rows if r["lang"] == lang), 3),
                      "language_detected_ok": round(statistics.mean(r["detected"] == lang for r in rows if r["lang"] == lang), 3)}
               for lang in ("en", "hi")}
    summary["stt_seconds_median"] = round(statistics.median(r["stt_s"] for r in rows), 2)
    (ROOT / "results" / "voice.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
