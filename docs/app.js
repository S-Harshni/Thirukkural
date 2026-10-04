'use strict';

// Keyword search in the browser (BM25 over the English explanation, the Tamil couplet and a Tamil commentary).
const STOP = new Set('a an the of to in on and or is are was be by for with as at that this it its from his her he she they them their who whom which what when where how does do did not no one ones'.split(' '));
const tokenize = t => (t.toLowerCase().match(/[a-z0-9]+|[஀-௿]+|[ऀ-ॿ]+/g) || []).filter(w => !STOP.has(w));
function buildIndex(docs, k1 = 1.5, b = 0.75) {
  const tf = docs.map(d => { const m = new Map(); for (const t of tokenize(d)) m.set(t, (m.get(t) || 0) + 1); return m; });
  const len = tf.map(m => [...m.values()].reduce((a, c) => a + c, 0)), avg = len.reduce((a, c) => a + c, 0) / len.length;
  const df = new Map(); for (const m of tf) for (const t of m.keys()) df.set(t, (df.get(t) || 0) + 1);
  const N = docs.length, idf = t => Math.log(1 + (N - (df.get(t) || 0) + 0.5) / ((df.get(t) || 0) + 0.5));
  return (q, k = 5) => {
    const qt = tokenize(q);
    return tf.map((m, i) => ({ i, s: qt.reduce((a, t) => { const f = m.get(t); return f ? a + idf(t) * f * (k1 + 1) / (f + k1 * (1 - b + b * len[i] / avg)) : a; }, 0) }))
      .filter(x => x.s > 0).sort((a, c) => c.s - a.s).slice(0, k);
  };
}

const METHODS = { bm25: 'Keywords (BM25)', dense: 'Dense multilingual (e5)', hybrid: 'Hybrid (rank fusion)' };
const pctCol = (label, key) => ({ label, key, num: true, format: v => v == null ? '–' : F.pct(v) });
const kuralCard = (k, extra) => h('div', { class: 'kural' },
  h('div', { class: 'ta', text: k.ta }), h('div', { class: 'en', text: k.en }),
  h('div', { class: 'com', text: k.com }), h('div', { class: 'meta', text: `Kural ${k.no} · ${k.ch} · ${k.sec}` }), extra || null);

const TABS = {
  Search(D) {
    const search = buildIndex(D.kurals.map(k => `${k.en} ${k.ta} ${k.com}`));
    const out = h('div', {});
    const input = h('input', { 'aria-label': 'Search', placeholder: 'Search the 1,330 couplets (English or Tamil words)', autocomplete: 'off' });
    function run(q) {
      input.value = q;
      const hits = search(q, 8);
      out.replaceChildren(hits.length ? h('p', { class: 'sub', text: `${hits.length} best matches (keyword search in your browser)` }) : h('p', { class: 'sub', text: 'No couplet contains these words. The dense search in the repository finds meaning across languages, including Hindi.' }),
        ...hits.map(x => kuralCard(D.kurals[x.i])));
    }
    const form = h('form', { class: 'ask', onsubmit: e => { e.preventDefault(); run(input.value); } }, input, h('button', { type: 'submit', text: 'Search' }));
    const chips = h('div', { class: 'chips' }, ['friendship', 'patience', 'learning', 'gratitude', 'anger', 'rain', 'நட்பு', 'கல்வி'].map(q => h('button', { type: 'button', text: q, onclick: () => run(q) })));
    const sec = section(intro('Search all 1,330 couplets. This page runs keyword search in your browser; the repository adds dense multilingual search (questions in Hindi find Tamil and English couplets) and the LLM tutor.'), form, chips, out);
    run('friendship');
    return sec;
  },

  'Ask the tutor'(D) {
    const out = h('div', {});
    function show(a) {
      out.replaceChildren(
        h('p', { class: 'sub', text: `Question (${a.lang === 'hi' ? 'Hindi' : 'English'})` }), h('p', { class: 'answer', text: a.q }),
        h('p', { class: 'sub', style: 'margin-top:12px', text: a.declined ? 'Tutor declined (off-topic)' : 'Tutor answer, citing only retrieved couplets' }),
        h('p', { class: 'answer', text: a.answer }), a.audio ? h('audio', { controls: true, preload: 'none', src: a.audio }) : null,
        ...(a.cited || []).map(n => kuralCard(D.kurals[n - 1])));
    }
    const sel = h('select', { 'aria-label': 'Question', onchange: e => show(D.answers[+e.target.value]) },
      D.answers.map((a, i) => h('option', { value: i, text: (a.lang === 'hi' ? '[हिंदी] ' : a.declined ? '[off-topic] ' : '') + a.q })));
    const sec = section(intro(`Recorded answers from the grounded tutor (${D.tutor_config}). It retrieves 3 couplets, answers in the language asked, must cite couplet numbers it was given and declines anything that is not about the Thirukkural. Answers are spoken with text to speech.`),
      h('div', { class: 'control' }, 'Question', sel), out);
    show(D.answers[0]);
    return sec;
  },

  Retrieval(D) {
    const R = D.retrieval, sets = [['chapter_themes', 'Chapter themes (133 titles)'], ['questions_en', 'Student questions, English'], ['questions_hi', 'Student questions, Hindi']];
    const series = Object.keys(METHODS).map((m, i) => ({ name: METHODS[m], color: [C.actual, C.model, C.baseline][i] }));
    return section(
      intro('Three ways to find the right couplet. Chapter titles are not in the searched text, so a chapter-theme query must be matched by meaning. Hindi questions share no words with the Tamil and English couplets: only the dense multilingual model can bridge them.'),
      grid(
        card({ title: 'Right couplet in the top 5', sub: 'Hit@5 by query set', legend: series.map(s2 => ({ ...s2, shape: 'box' })), wide: true,
          table: { columns: [{ label: 'Query set', key: 'set' }, ...Object.keys(METHODS).flatMap(m => [pctCol(METHODS[m] + ' hit@5', m + '5'), pctCol('MRR', m + 'm')])],
            rows: sets.map(([k, label]) => ({ set: label, ...Object.fromEntries(Object.keys(METHODS).flatMap(m => [[m + '5', R[m][k]['hit@5']], [m + 'm', R[m][k]['mrr@10']]])) })) } },
          plot => hbars(plot, { rows: sets.map(([k, label]) => ({ label, values: Object.keys(METHODS).map(m => R[m][k]['hit@5']) })), series, format: F.pct0, max: 1 })),
      ),
    );
  },

  Tutor(D) {
    const T = D.tutor;
    const rows = Object.entries(T).map(([k, v]) => ({ name: k.replace('zero_shot', 'Zero-shot').replace('few_shot', 'Few-shot').replace(':', ' · '), ...v }));
    return section(
      intro(`40 student questions asked in English and in Hindi (80), plus 30 unrelated questions (English and Hindi) that should be declined. Context: the top 3 couplets from dense search.`),
      grid(card({ title: 'Answer quality', wide: true, table: { columns: [
        { label: 'Prompt · model', key: 'name' }, pctCol('Cites the right couplet', 'cites_target'), pctCol('…when it was retrieved', 'cites_target_when_retrieved'),
        pctCol('Declines off-topic', 'declined_off_topic'), pctCol('Answers on-topic', 'answered_not_declined'), pctCol('Citations valid', 'citations_valid'),
        pctCol('Right language', 'language_ok'), pctCol('Valid JSON', 'json_ok'), { label: 'p50 ms', key: 'latency_p50_ms', num: true, format: F.int }], rows } }, null)),
    );
  },

  Voice(D) {
    const V = D.voice;
    if (!V) return section(intro('Voice results not generated yet.'));
    return section(
      intro('Spoken questions: 12 English and 12 Hindi questions were synthesized, transcribed by Whisper (small, on CPU) and searched. Retrieval from the transcript is compared with retrieval from the typed question.'),
      tiles([
        ['English: typed → spoken', `${F.pct0(V.summary.en['typed_hit@5'])} → ${F.pct0(V.summary.en['spoken_hit@5'])}`, 'right couplet in top 5'],
        ['Hindi: typed → spoken', `${F.pct0(V.summary.hi['typed_hit@5'])} → ${F.pct0(V.summary.hi['spoken_hit@5'])}`, 'right couplet in top 5'],
        ['Language detected', `${F.pct0(V.summary.en.language_detected_ok)} / ${F.pct0(V.summary.hi.language_detected_ok)}`, 'English / Hindi'],
        ['Whisper time', `${V.summary.stt_seconds_median}s`, 'median per question'],
      ]),
      grid(card({ title: 'Transcripts', wide: true, table: { columns: [{ label: 'Lang', key: 'lang' }, { label: 'Question', key: 'question' }, { label: 'Whisper heard', key: 'transcript' },
        { label: 'Typed hit@5', key: 'typed_hit5', render: v => h('span', { class: 'status' + (v ? '' : ' miss'), text: v ? 'yes' : 'no' }) },
        { label: 'Spoken hit@5', key: 'spoken_hit5', render: v => h('span', { class: 'status' + (v ? '' : ' miss'), text: v ? 'yes' : 'no' }) }], rows: V.rows } }, null)),
    );
  },
};

(async function main() {
  const D = await (await fetch('data.json')).json();
  document.getElementById('lede').textContent = 'All 1,330 couplets of the Thirukkural with semantic search across Tamil, English and Hindi, a grounded LLM tutor that cites the couplets it uses, and spoken questions through Whisper. Open-source models on a laptop; every part is measured.';
  document.getElementById('src').href = D.repo;
  if (D.app) { const a = document.getElementById('app'); a.href = D.app; a.hidden = false; }
  document.getElementById('foot').textContent = `Built by ${D.author}. English explanations: public-domain translation; Tamil commentary: மு. வரதராசனார்.`;
  const mainEl = document.getElementById('main'), nav = document.getElementById('tabs');
  const names = Object.keys(TABS), built = {};
  const slug = n => n.toLowerCase().replace(/\s+/g, '-');
  function open(name) {
    hideTip();
    for (const b of nav.children) b.setAttribute('aria-selected', String(b.textContent === name));
    for (const el of mainEl.children) el.hidden = true;
    built[name] ??= mainEl.appendChild(TABS[name](D));
    built[name].hidden = false;
    history.replaceState(null, '', '#' + slug(name));
    renderAll();
  }
  nav.append(...names.map(n => h('button', { type: 'button', role: 'tab', text: n, onclick: () => open(n) })));
  open(names.find(n => '#' + slug(n) === location.hash) || names[0]);
  let timer;
  addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(renderAll, 150); });
  const btn = document.getElementById('theme');
  const dark = () => (document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) === 'dark';
  btn.textContent = dark() ? 'Light mode' : 'Dark mode';
  btn.addEventListener('click', () => { document.documentElement.dataset.theme = dark() ? 'light' : 'dark'; btn.textContent = dark() ? 'Light mode' : 'Dark mode'; });
})();
