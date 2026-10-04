import json

from kuralai.bm25 import BM25, tokenize
from kuralai.corpus import chapters, load
from kuralai.search import Searcher
from kuralai.tutor import answer, messages


class Scripted:
    def __init__(self, text):
        self.text = text

    def chat(self, messages, **kw):
        return self.text, 5.0


def test_corpus_is_complete():
    kurals = load()
    assert len(kurals) == 1330 and len(chapters()) == 133
    assert kurals[0].chapter_en == "The Praise of God" and kurals[-1].section_en == "Love"
    assert "Kural 1 " not in kurals[0].passage(with_chapter=False)


def test_tokenizer_keeps_tamil_and_devanagari():
    assert tokenize("The Blessing of Rain") == ["blessing", "rain"]
    assert tokenize("வான்சிறப்பு") == ["வான்சிறப்பு"] and tokenize("बारिश") == ["बारिश"]


def test_bm25_ranks_the_matching_document_first():
    bm = BM25(["rain sustains the world", "friendship is precious", "learning is wealth"])
    scores = bm.scores("why is friendship precious")
    assert scores.index(max(scores)) == 1


def test_keyword_search_finds_a_known_couplet():
    s = Searcher(load(), dense=False)
    top = [k.no for k in s.search("help given at the right time though small is greater than the world", "bm25", k=5)]
    assert 102 in top


def test_tutor_validates_citations_and_language():
    kurals = load()
    ctx = [kurals[101], kurals[100]]
    ok = answer(Scripted(json.dumps({"answer": "Timely help is greater than the world.", "cited": [102], "declined": False})), "q", ctx, "en")
    assert ok.json_ok and ok.cited_valid and ok.lang_ok
    bad = answer(Scripted(json.dumps({"answer": "यह सही है।", "cited": [999], "declined": False})), "q", ctx, "en")
    assert not bad.cited_valid and not bad.lang_ok
    broken = answer(Scripted("no json here"), "q", ctx, "en")
    assert not broken.json_ok


def test_tamil_answers_are_verbatim_commentary():
    kurals = load()
    a = answer(None, "நட்பு", [kurals[0]], "ta")
    assert a.answer.startswith("குறள் 1:") and kurals[0].commentary_ta in a.answer


def test_few_shot_prompt_contains_examples_and_language():
    kurals = load()
    m = messages("q", kurals[:3], "hi", "few_shot", {k.no: k for k in kurals})
    assert "Examples (other questions)" in m[0]["content"] and m[1]["content"].endswith("Answer language: Hindi (Devanagari script).")
    assert "Examples" not in messages("q", kurals[:3], "en", "zero_shot")[0]["content"]
