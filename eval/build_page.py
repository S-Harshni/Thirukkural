"""Assemble docs/data.json for the live page and record spoken answers for the tutor demo (gTTS).

    python eval/build_page.py --repo https://github.com/S-Harshni/Thirukkural --author "S Harshni" --app https://thirukkural-evaz.onrender.com
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kuralai.corpus import load  # noqa: E402
from kuralai.voice import speak  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--author", required=True)
    ap.add_argument("--app")
    args = ap.parse_args()
    kurals = load()
    res = ROOT / "results"
    tutor = json.loads((res / "tutor.json").read_text(encoding="utf-8"))
    best = max(tutor["summary"], key=lambda k: (tutor["summary"][k]["cites_target"] + tutor["summary"][k]["declined_off_topic"]))
    rows = [r for r in tutor["rows"] if r["config"] == best]
    picks = [r for r in rows if r["target"] and r["lang"] == "en" and r["target"] in r["cited"]][:8]
    picks += [r for r in rows if r["target"] and r["lang"] == "hi" and r["target"] in r["cited"]][:4]
    picks += [r for r in rows if r["target"] is None and r["declined"]][:3]
    answers = []
    for r in picks:
        path, _ = speak(r["answer"], r["lang"], ROOT / "out" / "kuralai" / "answers")
        dest = ROOT / "docs" / "audio" / path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, dest)
        answers.append({"q": r["q"], "lang": r["lang"], "answer": r["answer"], "cited": r["cited"], "declined": r["declined"],
                        "audio": f"audio/{dest.name}"})
    voice = json.loads((res / "voice.json").read_text(encoding="utf-8")) if (res / "voice.json").exists() else None
    data = {
        "repo": args.repo, "author": args.author, "app": args.app, "tutor_config": best.replace(":", " · "),
        "kurals": [{"no": k.no, "ta": k.tamil, "en": k.english, "com": k.commentary_ta, "ch": k.chapter_en, "sec": k.section_en} for k in kurals],
        "retrieval": json.loads((res / "retrieval.json").read_text()), "tutor": tutor["summary"], "answers": answers, "voice": voice,
    }
    (ROOT / "docs" / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    print("docs/data.json", (ROOT / "docs" / "data.json").stat().st_size // 1024, "KB; best tutor:", best)


if __name__ == "__main__":
    main()
