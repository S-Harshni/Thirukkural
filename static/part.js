// static/part.js
// Behaviors for the /part/<paal> page (pager keyboard nav, roller alignment, audio, highlight scroll, etc.)

(() => {
  const audio = new Audio();
  const AUDIO_PLAYBACK_RATE = 1.18;
  const HIGHLIGHT_PROGRESS_SCALE = 0.965;
  let currentPlayingCard = null;
  let highlightState = null;
  let playbackSeq = 0;
  let playbackLabel = "▶️ ஒரு குறளின் ஒலி பொத்தானை அழுத்துங்கள்";
  let highlightTimer = null;

  const speakerPanel = document.querySelector(".speaker-panel");
  const speakerStatus = document.getElementById("speaker-status");
  const speakerNow = document.getElementById("speaker-now");
  const speakerStopBtn = document.getElementById("speaker-stop");
  const speakerWord = document.getElementById("speaker-word");
  const speakerBubble = document.getElementById("speaker-bubble");

  function configureAudioPlayback() {
    audio.defaultPlaybackRate = AUDIO_PLAYBACK_RATE;
    audio.playbackRate = AUDIO_PLAYBACK_RATE;
    if ("preservesPitch" in audio) audio.preservesPitch = true;
    if ("mozPreservesPitch" in audio) audio.mozPreservesPitch = true;
    if ("webkitPreservesPitch" in audio) audio.webkitPreservesPitch = true;
  }

  configureAudioPlayback();

  function getPageData() {
    const el = document.getElementById("page-data");
    if (!el) return {};
    try {
      return JSON.parse(el.textContent || "{}");
    } catch {
      return {};
    }
  }

  const pageData = getPageData();

  function setSpeaker({ speaking, statusText, nowText, disableStop }) {
    if (speakerPanel) speakerPanel.classList.toggle("speaking", Boolean(speaking));
    if (speakerStatus && typeof statusText === "string") speakerStatus.textContent = statusText;
    if (speakerNow && typeof nowText === "string") {
      playbackLabel = nowText;
      speakerNow.textContent = nowText;
    }
    if (speakerStopBtn) speakerStopBtn.disabled = Boolean(disableStop);
  }

  function setSpeakerWord(word) {
    if (!speakerWord) return;
    speakerWord.textContent = word && word.trim() ? word : "—";
    if (speakerBubble) {
      speakerBubble.classList.remove("pop");
      // Force a reflow to restart the pop animation
      void speakerBubble.offsetWidth;
      speakerBubble.classList.add("pop");
    }
  }

  function getCardText(card) {
    if (!card) return "";
    const lines = card.querySelector(".lines");
    if (!lines) return "";
    if (lines.dataset && lines.dataset.ttsText) return lines.dataset.ttsText;
    return (lines.innerText || "").toString();
  }

  function setPlaying(card, playing) {
    if (!card) return;
    if (playing) {
      card.dataset.playing = "true";
    } else {
      card.removeAttribute("data-playing");
    }
  }

  async function speak(text, key) {
    const res = await fetch("/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, key }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || "TTS failed");
    return data.audio;
  }

  async function playCard(card) {
    if (!card) return;
    const no = card.getAttribute("data-kural") || "";
    const text = getCardText(card) || card.innerText;
    const key = `kural_${no}`;
    const seq = ++playbackSeq;

    if (currentPlayingCard && currentPlayingCard !== card) {
      setPlaying(currentPlayingCard, false);
    }
    currentPlayingCard = card;
    setPlaying(card, true);

    initTtsWrapping(card);
    setHighlightCard(card);
    setSpeaker({
      speaking: false,
      statusText: "ஏற்றுகிறது…",
      nowText: no ? `குறள் ${no}` : "வாசிப்பு",
      disableStop: false,
    });
    setSpeakerWord("—");

    try {
      try {
        audio.pause();
        audio.currentTime = 0;
      } catch {}
      const src = await speak(text, key);
      if (seq !== playbackSeq) return;
      audio.src = src;
      configureAudioPlayback();
      await audio.play();
    } catch (e) {
      setPlaying(card, false);
      clearHighlight();
      setSpeaker({ speaking: false, statusText: "தயார்", nowText: "▶️ ஒரு குறளின் ஒலி பொத்தானை அழுத்துங்கள்", disableStop: true });
      console.error(e);
      alert("Audio failed. Please try again.");
    }
  }

  function toggleExplanation(card) {
    if (!card) return;
    if (card.dataset.open === "true") {
      card.removeAttribute("data-open");
    } else {
      card.dataset.open = "true";
    }
  }

  function initCards() {
    document.querySelectorAll(".kural-card").forEach((card) => {
      initTtsWrapping(card);
      card.addEventListener("click", (e) => {
        // If the play button was clicked, let that handler run.
        const target = e.target;
        if (target && target.closest && target.closest(".play-btn")) return;
        toggleExplanation(card);
      });
    });

    document.querySelectorAll(".play-btn[data-play]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        const no = btn.getAttribute("data-play");
        const card = document.getElementById(`kural-${no}`);
        playCard(card);
      });
    });

    audio.addEventListener("ended", () => {
      setPlaying(currentPlayingCard, false);
      stopHighlightLoop();
      clearHighlight();
      setSpeaker({ speaking: false, statusText: "தயார்", nowText: "▶️ ஒரு குறளின் ஒலி பொத்தானை அழுத்துங்கள்", disableStop: true });
    });

    audio.addEventListener("playing", () => {
      startHighlightLoop();
      updateWordHighlight();
      setSpeaker({ speaking: true, statusText: "பேசுகிறது…", nowText: playbackLabel || "வாசிப்பு", disableStop: false });
    });

    audio.addEventListener("pause", () => {
      stopHighlightLoop();
      if (audio.currentTime > 0 && audio.currentTime < (audio.duration || 0)) {
        setSpeaker({ speaking: false, statusText: "இடைநிறுத்தப்பட்டது", nowText: playbackLabel || "வாசிப்பு", disableStop: false });
      }
    });

    audio.addEventListener("timeupdate", () => {
      updateWordHighlight();
    });

    if (speakerStopBtn) {
      speakerStopBtn.addEventListener("click", () => {
        stopAudio();
      });
      speakerStopBtn.disabled = true;
    }
  }

  function initPlayAll() {
    window.playAll = async () => {
      const cards = [...document.querySelectorAll(".kural-card")];
      cards.forEach(initTtsWrapping);
      const texts = cards.map((card) => getCardText(card).trim()).filter(Boolean);
      if (!texts.length) return;
      const text = texts.join("\n");
      const key = `page_${pageData.paal || "paal"}_${pageData.page || "1"}`;
      const seq = ++playbackSeq;

      try {
        setPlaying(currentPlayingCard, false);
        currentPlayingCard = null;
        setHighlightPage();
        setSpeaker({ speaking: false, statusText: "ஏற்றுகிறது…", nowText: "இந்தப் பக்கம்", disableStop: false });
        setSpeakerWord("—");
        try {
          audio.pause();
          audio.currentTime = 0;
        } catch {}
        const src = await speak(text, key);
        if (seq !== playbackSeq) return;
        audio.src = src;
        configureAudioPlayback();
        await audio.play();
      } catch (e) {
        console.error(e);
        setSpeaker({ speaking: false, statusText: "தயார்", nowText: "▶️ ஒரு குறளின் ஒலி பொத்தானை அழுத்துங்கள்", disableStop: true });
        alert("Audio failed. Please try again.");
      }
    };
  }

  function initHighlightScroll() {
    const highlight = (pageData.highlight || "").toString().trim();
    const cameFromSearch = new URLSearchParams(window.location.search).has("search");
    if (!highlight || !cameFromSearch) return;

    const el = document.getElementById(`kural-${highlight}`);
    if (!el) return;

    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.dataset.highlight = "true";
    window.setTimeout(() => el.removeAttribute("data-highlight"), 4000);
  }

  function initKeyboardNav() {
    document.addEventListener("keydown", (e) => {
      const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : "";
      if (tag === "input" || tag === "textarea") return;

      if (e.key === "ArrowLeft" && pageData.prevUrl) window.location.href = pageData.prevUrl;
      if (e.key === "ArrowRight" && pageData.nextUrl) window.location.href = pageData.nextUrl;
      if (e.key.toLowerCase() === "t") window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initCards();
    initPlayAll();
    initHighlightScroll();
    initKeyboardNav();

    setSpeaker({ speaking: false, statusText: "தயார்", nowText: "▶️ ஒரு குறளின் ஒலி பொத்தானை அழுத்துங்கள்", disableStop: true });
    setSpeakerWord("—");
  });

  function stopAudio() {
    playbackSeq += 1; // invalidate any in-flight speak() promise
    try {
      audio.pause();
      audio.currentTime = 0;
    } catch {}
    setPlaying(currentPlayingCard, false);
    stopHighlightLoop();
    clearHighlight();
    setSpeaker({ speaking: false, statusText: "தயார்", nowText: "▶️ ஒரு குறளின் ஒலி பொத்தானை அழுத்துங்கள்", disableStop: true });
  }

  function initTtsWrapping(card) {
    if (!card) return;
    const linesEl = card.querySelector(".lines");
    if (!linesEl) return;
    if (linesEl.dataset.ttsWrapped === "1") return;

    const original = (linesEl.innerText || "").toString();
    linesEl.dataset.ttsWrapped = "1";
    linesEl.dataset.ttsText = original;

    const { fragment } = buildTtsFragment(original);
    linesEl.textContent = "";
    linesEl.appendChild(fragment);
  }

  function buildTtsFragment(text) {
    const fragment = document.createDocumentFragment();
    const lines = text.split(/\n/);
    let wordIndex = 0;
    for (let li = 0; li < lines.length; li++) {
      const line = lines[li] || "";
      const segments = line.split(/(\s+)/).filter((s) => s.length > 0);
      for (const seg of segments) {
        if (/^\s+$/.test(seg)) {
          fragment.appendChild(document.createTextNode(seg));
        } else {
          const span = document.createElement("span");
          span.className =
            "tts-word inline-block rounded-md px-1 py-0.5 transition data-[active=true]:bg-[#ead6c3] data-[active=true]:text-[#3a241e] data-[active=true]:shadow-sm";
          span.textContent = seg;
          span.dataset.lineIndex = String(li);
          span.dataset.wordIndex = String(wordIndex++);
          fragment.appendChild(span);
        }
      }
      if (li < lines.length - 1) fragment.appendChild(document.createElement("br"));
    }
    return { fragment };
  }

  function getWordUnits(span, nextSpan, mode) {
    const raw = (span?.textContent || "").trim();
    const bare = raw.replace(/[\s.,!?;:()[\]{}"'`~<>/\\|_-]+/g, "");
    const lengthUnits = Array.from(bare || raw).length;
    let units = Math.max(1.2, Math.min(4.8, 0.9 + lengthUnits * 0.16));

    if (/[,:;]$/.test(raw)) units += 0.45;
    if (/[.!?]$/.test(raw)) units += 0.8;
    if (/[।॥]$/.test(raw)) units += 1.1;

    if (!nextSpan) {
      units += mode === "page" ? 2.8 : 1.6;
      return units;
    }

    if (span.dataset.lineIndex !== nextSpan.dataset.lineIndex) {
      units += 1.1;
    }

    const currentCard = span.closest(".kural-card");
    const nextCard = nextSpan.closest(".kural-card");
    if (currentCard && nextCard && currentCard !== nextCard) {
      units += 2.2;
    }

    return units;
  }

  function buildHighlightTimeline(spans, mode) {
    if (!spans.length) return [];

    let totalUnits = mode === "page" ? 2.4 : 1.5;
    const cumulativeUnits = spans.map((span, idx) => {
      totalUnits += getWordUnits(span, spans[idx + 1] || null, mode);
      return totalUnits;
    });

    return cumulativeUnits.map((units) => units / totalUnits);
  }

  function findHighlightIndex(timeline, progress) {
    if (!timeline.length) return -1;
    let low = 0;
    let high = timeline.length - 1;

    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (progress <= timeline[mid]) {
        high = mid;
      } else {
        low = mid + 1;
      }
    }

    return low;
  }

  function setHighlightCard(card) {
    if (!card) return;
    clearHighlight();
    const spans = [...card.querySelectorAll(".lines .tts-word")];
    if (!spans.length) return;
    highlightState = { card, spans, activeIndex: -1, mode: "card", timeline: buildHighlightTimeline(spans, "card") };
  }

  function setHighlightPage() {
    clearHighlight();
    const spans = [...document.querySelectorAll(".kural-card .lines .tts-word")];
    if (!spans.length) return;
    highlightState = { card: null, spans, activeIndex: -1, mode: "page", timeline: buildHighlightTimeline(spans, "page") };
  }

  function clearHighlight() {
    if (!highlightState) return;
    const { spans, activeIndex } = highlightState;
    if (activeIndex >= 0 && spans[activeIndex]) spans[activeIndex].removeAttribute("data-active");
    highlightState = null;
    setSpeakerWord("—");
  }

  function updateWordHighlight() {
    if (!highlightState) return;
    const dur = audio.duration;
    if (!dur || !isFinite(dur) || dur <= 0) return;
    const { spans, activeIndex, mode, timeline } = highlightState;
    const n = spans.length;
    if (!n || !timeline?.length) return;

    const rawProgress = Math.max(0, Math.min(audio.currentTime / dur, 1));
    const progress =
      rawProgress >= 0.985 ? 0.999999 : Math.max(0, Math.min(rawProgress * HIGHLIGHT_PROGRESS_SCALE, 0.999999));
    const idx = findHighlightIndex(timeline, progress);
    if (idx === activeIndex) return;

    if (activeIndex >= 0 && spans[activeIndex]) spans[activeIndex].removeAttribute("data-active");
    if (spans[idx]) spans[idx].setAttribute("data-active", "true");
    highlightState.activeIndex = idx;
    if (spans[idx]) setSpeakerWord(spans[idx].textContent || "");

    if (mode === "page" && spans[idx]) {
      const card = spans[idx].closest(".kural-card");
      if (card && card !== currentPlayingCard) {
        setPlaying(currentPlayingCard, false);
        currentPlayingCard = card;
        setPlaying(currentPlayingCard, true);
      }
    }
  }

  function startHighlightLoop() {
    if (highlightTimer) return;
    highlightTimer = window.setInterval(() => {
      if (audio.paused) return;
      updateWordHighlight();
    }, 80);
  }

  function stopHighlightLoop() {
    if (!highlightTimer) return;
    window.clearInterval(highlightTimer);
    highlightTimer = null;
  }
})();
