"""Grounded Thirukkural tutor: retrieve couplets, then let a local LLM answer in English or Hindi citing only them.

The model must return {"answer", "cited", "declined"}. Code checks that every cited couplet was actually retrieved,
that the answer is in the language asked for, and that unrelated questions are declined. For Tamil the tutor does not
generate text at all: it returns the couplet and the classical commentary verbatim, which a 3B model cannot match.
"""
import json
import re
from dataclasses import dataclass

from .corpus import Kural

LANG_NAMES = {"en": "English", "hi": "Hindi (Devanagari script)"}
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
TAMIL = re.compile(r"[஀-௿]")

SYSTEM = """You are a patient tutor of the Thirukkural, the classical Tamil text of 1,330 couplets by Thiruvalluvar.
Answer the student's question using ONLY the couplets given below. Cite the couplet numbers you used.
If none of the couplets answers the question, or the question is not about the Thirukkural's teachings, set
"declined": true and say politely that you can only discuss the Thirukkural.
Write 2-4 short sentences in {lang}, simple enough to read aloud. Do not invent couplets, numbers or quotes.
Return one JSON object only: {{"answer": "...", "cited": [couplet numbers], "declined": true or false}}"""

EXAMPLES = [
    {"q": "What does Valluvar say about returning a favour?", "ctx": [102],
     "out": {"answer": "Valluvar says a help given at the right time, however small, is greater than the whole world. "
                       "So we should value and remember such help (Kural 102).", "cited": [102], "declined": False}},
    {"q": "सोने का आज का भाव क्या है?", "ctx": [],
     "out": {"answer": "माफ़ कीजिए, मैं केवल तिरुक्कुरल की शिक्षाओं के बारे में बात कर सकता हूँ।", "cited": [], "declined": True}},
]


@dataclass
class Answer:
    answer: str
    cited: list
    declined: bool
    json_ok: bool
    cited_valid: bool
    lang_ok: bool
    ms: float


def _context(kurals: list[Kural]) -> str:
    return "\n".join(f"[{k.no}] {k.passage()}" for k in kurals)


def messages(question: str, kurals: list[Kural], lang: str, variant: str, examples_ctx: dict | None = None) -> list[dict]:
    system = SYSTEM.format(lang=LANG_NAMES[lang])
    if variant == "few_shot":
        shots = []
        for ex in EXAMPLES:
            ctx = _context([examples_ctx[n] for n in ex["ctx"]]) if examples_ctx and ex["ctx"] else "(no relevant couplets)"
            shots.append(f"Couplets:\n{ctx}\nQuestion: {ex['q']}\nOutput: {json.dumps(ex['out'], ensure_ascii=False)}")
        system += "\n\nExamples (other questions):\n\n" + "\n\n".join(shots)
    user = f"Couplets:\n{_context(kurals)}\nQuestion: {question}\nAnswer language: {LANG_NAMES[lang]}."
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        out = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    return out if isinstance(out, dict) else None


def answer(llm, question: str, kurals: list[Kural], lang: str, variant: str = "few_shot", examples_ctx=None, seed=0) -> Answer:
    if lang == "ta":
        top = kurals[0]
        return Answer(f"குறள் {top.no}: {top.tamil} — {top.commentary_ta}", [top.no], False, True, True, True, 0.0)
    text, ms = llm.chat(messages(question, kurals, lang, variant, examples_ctx), json_mode=True, temperature=0.2, seed=seed,
                        max_tokens=260)
    out = _parse(text)
    json_ok = out is not None and isinstance(out.get("answer"), str)
    out = out or {}
    cited = [int(c) for c in out.get("cited", []) if str(c).isdigit()] if isinstance(out.get("cited"), list) else []
    retrieved = {k.no for k in kurals}
    ans = str(out.get("answer", ""))
    has_hi = bool(DEVANAGARI.search(ans))
    lang_ok = (has_hi if lang == "hi" else not has_hi and not TAMIL.search(ans)) if ans else False
    return Answer(ans, cited, bool(out.get("declined", False)), json_ok, all(c in retrieved for c in cited), lang_ok, ms)
