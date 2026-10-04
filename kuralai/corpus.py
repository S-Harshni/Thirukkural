"""The 1,330 couplets as search documents: Tamil text, English explanation, chapter, section and a Tamil commentary."""
import json
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
SECTIONS_EN = {"அறத்துப்பால்": "Virtue", "பொருட்பால்": "Wealth", "காமத்துப்பால்": "Love"}


@dataclass
class Kural:
    no: int
    tamil: str
    english: str
    chapter_no: int
    chapter_en: str
    chapter_ta: str
    section_en: str
    commentary_ta: str  # மு. வரதராசனார் உரை (short, modern Tamil)

    def passage(self, with_chapter: bool = True) -> str:
        """Context for the tutor (with chapter) or the searchable text (without it, so chapter-theme queries cannot
        simply match the chapter title)."""
        head = f"Kural {self.no} ({self.section_en} / {self.chapter_en}): " if with_chapter else ""
        return f"{head}{self.english} | {self.tamil} | {self.commentary_ta}"


def _chapters() -> list[dict]:
    detail = json.loads((DATA / "detail.json").read_text(encoding="utf-8"))
    out = []
    for section in detail[0]["section"]["detail"]:
        for group in section["chapterGroup"]["detail"]:
            for ch in group["chapters"]["detail"]:
                out.append({**ch, "section": section["translation"]})
    return out


def load() -> list[Kural]:
    raw = json.loads((DATA / "thirukkural.json").read_text(encoding="utf-8"))["kural"]
    meanings = json.loads((DATA / "thirukkural_meanings.json").read_text(encoding="utf-8"))
    chapters = _chapters()
    by_no = {}
    for ch in chapters:
        for n in range(ch["start"], ch["end"] + 1):
            by_no[n] = ch
    kurals = []
    for k in raw:
        n = int(k["Number"])
        ch = by_no[n]
        m = meanings.get(str(n), {})
        commentary = (m.get("mu_varadha") or m.get("salaman_papa") or "").split(":", 1)[-1].strip()
        kurals.append(Kural(n, f"{k['Line1']} {k['Line2']}", k["explanation"].strip(), ch["number"], ch["translation"],
                            ch["name"], ch["section"], commentary))
    return kurals


def chapters() -> list[dict]:
    return _chapters()
