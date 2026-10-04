"""Speech for the tutor: questions are transcribed with Whisper (faster-whisper, int8 CPU) and answers are spoken with
gTTS in English, Hindi or Tamil."""
import hashlib
import time
from pathlib import Path

import numpy as np

VOICES = {"en": ("en", "co.in"), "hi": ("hi", "co.in"), "ta": ("ta", "co.in")}
_WHISPER = {}


def speak(text: str, lang: str, out_dir: Path) -> tuple[Path, float]:
    from gtts import gTTS
    voice, tld = VOICES.get(lang, VOICES["en"])
    path = out_dir / f"{hashlib.sha1(f'{voice}|{text}'.encode()).hexdigest()[:16]}.mp3"
    if path.exists():
        return path, 0.0
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    gTTS(text=text, lang=voice, tld=tld).save(str(path))
    return path, time.perf_counter() - start


def load_audio(path: Path) -> np.ndarray:
    """Decode to 16 kHz mono float32."""
    import av
    container = av.open(str(path))
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16_000)
    chunks = [o.to_ndarray().reshape(-1) for f in container.decode(audio=0) for o in resampler.resample(f)]
    chunks += [o.to_ndarray().reshape(-1) for o in resampler.resample(None)]
    container.close()
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def transcribe(samples: np.ndarray, size: str = "small") -> dict:
    if size not in _WHISPER:
        from faster_whisper import WhisperModel
        _WHISPER[size] = WhisperModel(size, device="cpu", compute_type="int8", cpu_threads=4)
    segments, info = _WHISPER[size].transcribe(samples, beam_size=1)
    return {"text": " ".join(s.text.strip() for s in segments).strip(), "language": info.language}
