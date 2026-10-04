"""Ask the Thirukkural tutor from the terminal (needs Ollama running locally).

    python ask.py "What does Valluvar say about friendship?"
    python ask.py "दोस्ती के बारे में वल्लुवर क्या कहते हैं?" --lang hi
    python ask.py "நட்பு பற்றி" --lang ta          # Tamil: couplet + classical commentary, verbatim
    python ask.py --voice question.mp3              # transcribe a spoken question with Whisper first
"""
import argparse

from kuralai.corpus import load
from kuralai.llm import ChatModel
from kuralai.search import Searcher
from kuralai.tutor import answer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?")
    ap.add_argument("--lang", choices=["en", "hi", "ta"])
    ap.add_argument("--voice", help="audio file with the spoken question")
    ap.add_argument("--model", default="qwen2.5:3b")
    args = ap.parse_args()
    question = args.question
    if args.voice:
        from kuralai.voice import load_audio, transcribe
        res = transcribe(load_audio(args.voice))
        question, args.lang = res["text"], args.lang or ("hi" if res["language"] == "hi" else "ta" if res["language"] == "ta" else "en")
        print(f"Heard ({res['language']}): {question}")
    lang = args.lang or "en"
    kurals = load()
    by_no = {k.no: k for k in kurals}
    found = Searcher(kurals).search(question, "dense", k=3)
    a = answer(ChatModel(args.model), question, found, lang, "few_shot", examples_ctx=by_no)
    print("\n" + a.answer)
    for n in a.cited:
        k = by_no[n]
        print(f"\nKural {n} · {k.chapter_en}\n  {k.tamil}\n  {k.english}")


if __name__ == "__main__":
    main()
