#!/usr/bin/env python3
"""Render a lesson.json (plus its extracted figures) into one self-contained lecture.html.

Usage: render.py <lesson.json> [out.html]

Everything is inlined, so the result is a single file that works offline, opens
from anywhere, and can be dropped into a vault. Narration uses the browser's
speech synthesis unless narrate.py has produced audio/, in which case the m4a
files are inlined and used instead.
"""
import base64
import io
import json
import os
import sys

MAX_W = 1600          # downscale figures wider than this before inlining


def b64_png(path):
    """Inline a figure, halving it until it is under MAX_W so the page stays small.

    Figures are extracted at 200 dpi so the zoom view has detail to show; that is
    more than the inline view needs.
    """
    data = open(path, "rb").read()
    try:
        import fitz                                  # already a dependency of extract.py
        pix = fitz.Pixmap(path)
        while pix.width > MAX_W:
            pix.shrink(1)                            # each call halves both dimensions
        if pix.width < fitz.Pixmap(path).width:
            data = pix.tobytes("png")
    except Exception:
        pass                                          # inline the original; size is not worth a crash
    return "data:image/png;base64," + base64.b64encode(data).decode()


AUDIO_MIME = {".m4a": "audio/mp4", ".wav": "audio/wav", ".aiff": "audio/aiff"}


def find_audio(audio_dir, n):
    """narrate.py emits m4a where afconvert exists and wav where it does not,
    so look for either rather than assuming macOS."""
    for ext in AUDIO_MIME:
        p = os.path.join(audio_dir, f"{n:02d}{ext}")
        if os.path.exists(p):
            return p
    return None


def b64_audio(path):
    mime = AUDIO_MIME.get(os.path.splitext(path)[1], "audio/mpeg")
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
  :root{
    --bg:#faf8f5; --fg:#1a1a1a; --dim:#6b6b6b; --line:#e2ddd5;
    --accent:#8a5a2b; --card:#fff; --ok:#2c6e49; --shadow:0 1px 3px rgba(0,0,0,.07);
  }
  @media (prefers-color-scheme:dark){
    :root{ --bg:#14161a; --fg:#e8e6e3; --dim:#9aa0a6; --line:#2a2e35;
           --accent:#d9a441; --card:#1b1e24; --ok:#7fb069; --shadow:0 1px 3px rgba(0,0,0,.4); }
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{background:var(--bg);color:var(--fg);
       font:16px/1.6 ui-serif,Georgia,'Iowan Old Style',serif;
       display:flex;flex-direction:column}
  header{padding:.7rem 1.2rem;border-bottom:1px solid var(--line);
         display:flex;gap:1rem;align-items:baseline;flex-wrap:wrap}
  header b{font-size:.95rem;font-weight:600}
  header span{color:var(--dim);font-size:.8rem;
              font-family:ui-sans-serif,system-ui,sans-serif}
  #bar{height:3px;background:var(--line)}
  #bar div{height:100%;width:0;background:var(--accent);transition:width .3s}
  main{flex:1;overflow-y:auto;padding:2rem 1.2rem 6rem}
  .slide{max-width:60rem;margin:0 auto;display:none}
  .slide.on{display:block;animation:fade .35s ease}
  @keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
  h2{font-size:1.55rem;line-height:1.25;margin:0 0 1.1rem;letter-spacing:-.01em}
  .kicker{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.7rem;
          letter-spacing:.12em;text-transform:uppercase;color:var(--accent);
          margin-bottom:.5rem;font-weight:600}
  ul{padding-left:1.1rem;margin:0 0 1.3rem}
  li{margin:.5rem 0}
  figure{margin:1.3rem 0;background:var(--card);border:1px solid var(--line);
         border-radius:10px;padding:.9rem;box-shadow:var(--shadow)}
  figure img{width:100%;height:auto;display:block;border-radius:4px;cursor:zoom-in}
  figcaption{font-family:ui-sans-serif,system-ui,sans-serif;font-size:.78rem;
             color:var(--dim);margin-top:.7rem;line-height:1.5}
  figcaption b{color:var(--accent)}
  .check{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
         border-radius:8px;padding:1rem 1.1rem;margin:1.4rem 0}
  .check p{margin:0 0 .8rem;font-weight:600}
  .check .ans{display:none;border-top:1px solid var(--line);padding-top:.8rem;margin-top:.3rem}
  .check.open .ans{display:block;animation:fade .3s}
  .check.open > button{display:none}
  .check .ans b{color:var(--ok)}
  .check textarea{width:100%;margin:0 0 .7rem;padding:.6rem .7rem;border-radius:6px;
                  border:1px solid var(--line);background:var(--bg);color:var(--fg);
                  font:inherit;font-size:.92rem;resize:vertical}
  .check textarea:focus{outline:none;border-color:var(--accent)}
  .check.open textarea{opacity:.6}
  button[disabled]{opacity:.4;cursor:not-allowed}
  .grade{display:flex;gap:.5rem;align-items:center;margin-top:.9rem;
         font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem;color:var(--dim)}
  .check.graded .grade{display:none}
  .verdict{margin-top:.9rem;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem}
  button{font:inherit;font-family:ui-sans-serif,system-ui,sans-serif;font-size:.82rem;
         padding:.42rem .9rem;border:1px solid var(--line);background:var(--card);
         color:var(--fg);border-radius:6px;cursor:pointer}
  button:hover{border-color:var(--accent)}
  footer{position:fixed;bottom:0;left:0;right:0;background:var(--bg);
         border-top:1px solid var(--line);padding:.6rem 1.2rem;
         display:flex;gap:.6rem;align-items:center;
         font-family:ui-sans-serif,system-ui,sans-serif;font-size:.8rem}
  footer .sp{flex:1}
  footer .hint{color:var(--dim);font-size:.72rem}
  #zoom{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;
        align-items:center;justify-content:center;z-index:50;cursor:zoom-out;padding:2rem}
  #zoom.on{display:flex}
  #zoom img{max-width:100%;max-height:100%;object-fit:contain}
  #askwrap{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;
           align-items:center;justify-content:center;z-index:60;padding:1.5rem}
  #askwrap.on{display:flex}
  #askbox{background:var(--card);border:1px solid var(--line);border-radius:12px;
          padding:1.3rem;max-width:38rem;width:100%;box-shadow:0 8px 40px rgba(0,0,0,.4)}
  #askbox p{margin:0 0 .8rem}
  #askbox textarea{width:100%;padding:.7rem;border-radius:7px;border:1px solid var(--line);
                   background:var(--bg);color:var(--fg);font:inherit;font-size:.95rem;resize:vertical}
  .askrow{display:flex;gap:.5rem;margin-top:.9rem}
  #askcopy[hidden]{display:none}
  .big{background:var(--card);border:1px solid var(--line);border-radius:10px;
       padding:1.2rem 1.3rem;margin:0 0 1.4rem;box-shadow:var(--shadow)}
  .big p{margin:0}
  #cap{position:fixed;left:0;right:0;bottom:3.1rem;display:none;justify-content:center;
       padding:0 1rem;pointer-events:none;z-index:40}
  #cap.on{display:flex}
  #cap span{background:rgba(12,12,14,.92);color:#f4f2ef;max-width:52rem;
            padding:.55rem .95rem;border-radius:8px;text-align:center;
            font-family:ui-sans-serif,system-ui,sans-serif;font-size:.95rem;line-height:1.45;
            box-shadow:0 2px 14px rgba(0,0,0,.35)}
  /* focus: dim the slide, lift the thing being talked about */
  .slide.focusing [data-focus]{opacity:.32;transition:opacity .35s ease}
  .slide.focusing [data-focus].hot{opacity:1}
  .slide.focusing figure[data-focus].hot{box-shadow:0 0 0 2px var(--accent),var(--shadow)}
  .slide.focusing li[data-focus].hot{font-weight:600}
  @media (max-width:640px){ main{padding:1.2rem .9rem 6rem} h2{font-size:1.3rem}
                            #cap span{font-size:.85rem} }
  @media (prefers-reduced-motion:reduce){ *{animation:none!important;transition:none!important} }
</style></head><body>
<header><b>__PAPER__</b><span>__VENUE__</span></header>
<div id="bar"><div></div></div>
<main id="deck">__SLIDES__</main>
<div id="cap"><span></span></div>
<footer>
  <button id="prev">&larr;</button>
  <button id="cc" title="Toggle subtitles">CC</button>
  <button id="next">&rarr;</button>
  <button id="say">▶ Narrate</button>
  <button id="ask" title="Ask about this slide">? Ask</button>
  <button id="askcopy" title="Copy every question for Claude">Copy questions</button>
  <span class="sp"></span>
  <span id="score" class="hint"></span>
  <span class="hint">&larr;&rarr; move · space play/pause · CC subtitles · click figure to zoom</span>
  <span id="pos"></span>
</footer>
<div id="zoom"><img alt=""></div>
<div id="askwrap">
  <div id="askbox">
    <p>What is confusing about <b id="askslide"></b>?</p>
    <textarea id="askq" rows="3" placeholder="Say it however it comes out. Half-formed is fine, that is usually where the confusion actually is."></textarea>
    <div class="askrow">
      <button id="asksave">Save question</button>
      <button id="askcancel">Cancel</button>
    </div>
  </div>
</div>
<script>
const DATA = __DATA__;
const deck = document.getElementById('deck');
const slides = [...deck.querySelectorAll('.slide')];
let i = 0, audio = null;
const KEY = 'paper-lecture:' + document.title;
const capEl = document.getElementById('cap');
let ccOn = localStorage.getItem('paper-lecture:cc') !== 'off';
const score = JSON.parse(localStorage.getItem(KEY) || '{}');

function show(n){
  stop();
  i = Math.max(0, Math.min(slides.length - 1, n));
  slides.forEach((s, k) => s.classList.toggle('on', k === i));
  document.querySelector('#bar div').style.width = ((i + 1) / slides.length * 100) + '%';
  document.getElementById('pos').textContent = (i + 1) + ' / ' + slides.length;
  deck.scrollTop = 0;
}
function stop(){
  window.speechSynthesis && speechSynthesis.cancel();
  if (audio){ audio.pause(); audio = null; }
  document.getElementById('say').textContent = '▶ Narrate';
}
function clearFocus(){
  slides.forEach(sl => {
    sl.classList.remove('focusing');
    sl.querySelectorAll('[data-focus]').forEach(e => e.classList.remove('hot'));
  });
  capEl.classList.remove('on');
  capEl.firstElementChild.textContent = '';
}
// Show the sentence being spoken, and lift the one thing it is about.
function paint(cue){
  if (!cue) return;
  if (ccOn){
    capEl.firstElementChild.textContent = cue.s;
    capEl.classList.add('on');
  }
  const sl = slides[i];
  const target = cue.f ? sl.querySelector('[data-focus="' + cue.f + '"]') : null;
  sl.querySelectorAll('[data-focus]').forEach(e => e.classList.remove('hot'));
  if (target){ sl.classList.add('focusing'); target.classList.add('hot'); }
  else sl.classList.remove('focusing');
}
function label(state){
  document.getElementById('say').textContent =
    state === 'playing' ? '\u23f8 Pause' : state === 'paused' ? '\u25b6 Resume' : '\u25b6 Narrate';
}
// Space and the button toggle: start, then pause, then resume from where it
// stopped. Cancelling and restarting from the top is not a pause.
function toggle(){
  if (audio){
    if (audio.paused){ audio.play(); label('playing'); }
    else { audio.pause(); label('paused'); }
    return;
  }
  if (window.speechSynthesis && speechSynthesis.speaking){
    if (speechSynthesis.paused){ speechSynthesis.resume(); label('playing'); }
    else { speechSynthesis.pause(); label('paused'); }
    return;
  }
  narrate();
}
function narrate(){
  const cues = (DATA.cues && DATA.cues[i]) || null;
  const t = DATA.narration[i];
  if (!t) return;
  label('playing');

  if (DATA.audio && DATA.audio[i]){
    audio = new Audio(DATA.audio[i]);
    if (cues){
      let last = -1;
      audio.ontimeupdate = () => {
        const now = audio.currentTime;
        let k = cues.findIndex(c => now >= c.t && now < c.t + c.d);
        if (k === -1 && now >= cues[cues.length-1].t) k = cues.length - 1;
        if (k !== -1 && k !== last){ last = k; paint(cues[k]); }
      };
    }
    audio.onended = () => { audio = null; clearFocus(); label('idle'); };
    audio.play();
    return;
  }

  // Browser voice: no timeline, so speak one sentence at a time and advance
  // the caption as each finishes. Same cue list, so focus still works.
  const list = cues || [{s: t, f: null}];
  let k = 0;
  const speakNext = () => {
    if (k >= list.length){ clearFocus(); label('idle'); return; }
    paint(list[k]);
    const u = new SpeechSynthesisUtterance(list[k].s);
    u.rate = 1.0;
    const v = speechSynthesis.getVoices().find(v => /Samantha|Ava|Serena|Daniel/.test(v.name));
    if (v) u.voice = v;
    u.onend = () => { k++; speakNext(); };
    speechSynthesis.speak(u);
  };
  speakNext();
}
document.getElementById('prev').onclick = () => show(i - 1);
document.getElementById('next').onclick = () => show(i + 1);
document.getElementById('say').onclick = toggle;
document.getElementById('cc').onclick = () => {
  ccOn = !ccOn;
  localStorage.setItem('paper-lecture:cc', ccOn ? 'on' : 'off');
  document.getElementById('cc').style.opacity = ccOn ? 1 : .45;
  if (!ccOn) capEl.classList.remove('on');
};
document.getElementById('cc').style.opacity = ccOn ? 1 : .45;
document.addEventListener('keydown', e => {
  // The quiz box needs its own spacebar.
  if (e.target.matches('textarea, input, [contenteditable]')) return;
  if (e.key === '?' || (e.key === '/' && e.shiftKey)){ e.preventDefault(); openAsk(); return; }
  if (e.key === 'Escape' && askWrap.classList.contains('on')){ closeAsk(); return; }
  if (e.key === 'ArrowRight') show(i + 1);
  else if (e.key === 'ArrowLeft') show(i - 1);
  else if (e.key === ' '){ e.preventDefault(); toggle(); }
  else if (e.key === 'Escape') document.getElementById('zoom').classList.remove('on');
});
// Retrieval practice: you have to produce an answer before you can see one.
// Recognising a correct answer feels like knowing it and does not stick;
// generating one, even wrongly, is what builds the memory.
deck.addEventListener('input', e => {
  if (e.target.tagName === 'TEXTAREA'){
    const b = e.target.closest('.check').querySelector('button[data-reveal]');
    b.disabled = e.target.value.trim().length < 8;
  }
});
deck.addEventListener('click', e => {
  if (e.target.tagName === 'IMG'){
    const z = document.getElementById('zoom');
    z.querySelector('img').src = e.target.src;
    z.classList.add('on');
  }
  if (e.target.dataset.reveal) e.target.closest('.check').classList.add('open');
  if (e.target.dataset.grade){
    const c = e.target.closest('.check');
    const missed = e.target.dataset.grade === 'miss';
    c.classList.add('graded');
    const v = document.createElement('div');
    v.className = 'verdict';
    v.textContent = missed
      ? 'Marked for review. This one goes in the Anki deck at the top of the pile.'
      : 'Good. It still needs a second pass in a few days to hold.';
    c.querySelector('.ans').appendChild(v);
    score[slides.indexOf(c.closest('.slide'))] = missed ? 0 : 1;
    localStorage.setItem(KEY, JSON.stringify(score));
    tally();
  }
});
function tally(){
  const vals = Object.values(score);
  const el = document.getElementById('score');
  if (!vals.length){ el.textContent = ''; return; }
  el.textContent = 'recalled ' + vals.filter(v => v).length + '/' + vals.length;
}
document.getElementById('zoom').onclick = e => e.currentTarget.classList.remove('on');
// Asking a question is the thing a static lecture cannot do. So capture it with
// the slide it belongs to and hand the whole lot back to Claude in one paste.
const QKEY = KEY + ':questions';
let questions = JSON.parse(localStorage.getItem(QKEY) || '[]');
const askWrap = document.getElementById('askwrap');
const askQ = document.getElementById('askq');

function refreshAsk(){
  const b = document.getElementById('askcopy');
  b.hidden = questions.length === 0;
  b.textContent = 'Copy ' + questions.length + ' question' + (questions.length === 1 ? '' : 's');
}
function openAsk(){
  document.getElementById('askslide').textContent = slides[i].querySelector('h2').textContent;
  askQ.value = '';
  askWrap.classList.add('on');
  askQ.focus();
}
function closeAsk(){ askWrap.classList.remove('on'); }

document.getElementById('ask').onclick = openAsk;
document.getElementById('askcancel').onclick = closeAsk;
document.getElementById('asksave').onclick = () => {
  const q = askQ.value.trim();
  if (!q) { closeAsk(); return; }
  questions.push({n: i + 1, slide: slides[i].querySelector('h2').textContent, q: q});
  localStorage.setItem(QKEY, JSON.stringify(questions));
  refreshAsk();
  closeAsk();
};
document.getElementById('askcopy').onclick = async () => {
  const lines = questions.map(x => '- Slide ' + x.n + ', "' + x.slide + '"\n  ' + x.q);
  const text = 'I went through the lecture on ' + DATA.paper +
    ' and got stuck on these. Answer each one, and tell me if any of them mean a slide '
    + 'is badly explained rather than me missing something.\n\n' + lines.join('\n');
  try {
    await navigator.clipboard.writeText(text);
    const b = document.getElementById('askcopy');
    const old = b.textContent; b.textContent = 'Copied, paste to Claude';
    setTimeout(() => { b.textContent = old; }, 2200);
  } catch (err) {
    // clipboard is blocked on file:// in some browsers; show it to copy by hand
    askQ.value = text; document.getElementById('askslide').textContent = 'all slides';
    askWrap.classList.add('on'); askQ.select();
  }
};
askWrap.onclick = e => { if (e.target === askWrap) closeAsk(); };

refreshAsk();
tally();
show(0);
</script></body></html>"""


def esc(s):
    """HTML-escape. Quotes included: this output also lands inside attributes."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def js_json(obj):
    """JSON safe to drop inside a <script> block.

    `<` only ever occurs inside string literals here, and \\u003c is valid JSON,
    so escaping it cannot corrupt the structure but does stop a narration
    containing "</script>" from closing the tag early.
    """
    return json.dumps(obj).replace("<", "\\u003c")


def build_slide(s, figdir):
    out = ['<section class="slide">']
    if s.get("kicker"):
        out.append(f'<div class="kicker">{esc(s["kicker"])}</div>')
    out.append(f'<h2>{esc(s["title"])}</h2>')
    if s.get("big"):
        out.append(f'<div class="big" data-focus="big"><p>{esc(s["big"])}</p></div>')
    if s.get("points"):
        out.append("<ul>" + "".join(
            f'<li data-focus="point:{n}">{esc(p)}</li>' for n, p in enumerate(s["points"])) + "</ul>")
    if s.get("figure"):
        path = os.path.join(figdir, s["figure"])
        if os.path.exists(path):
            cap = f'<b>{esc(s.get("figureLabel", "Figure"))}.</b> {esc(s.get("figureNote", ""))}'
            out.append(f'<figure data-focus="figure"><img alt="{esc(s.get("figureLabel",""))}" '
                       f'src="{b64_png(path)}"><figcaption>{cap}</figcaption></figure>')
        else:
            print(f"  warning: missing figure {s['figure']}", file=sys.stderr)
    if s.get("check"):
        c = s["check"]
        out.append(
            '<div class="check"><p>' + esc(c["q"]) + "</p>"
            '<textarea rows="2" placeholder="Answer from memory first. Typing it is '
            'what makes it stick, even if you are wrong."></textarea>'
            '<button data-reveal="1" disabled>Show answer</button>'
            '<div class="ans"><p><b>' + esc(c["a"]) + "</b></p>"
            + (f"<p>{esc(c['why'])}</p>" if c.get("why") else "")
            + '<div class="grade"><span>Did you have it?</span>'
              '<button data-grade="got">Yes</button>'
              '<button data-grade="miss">No</button></div>'
            + "</div></div>")
    out.append("</section>")
    return "".join(out)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: render.py <lesson.json> [out.html]")
    lpath = sys.argv[1]
    lesson = json.load(open(lpath))
    base = os.path.dirname(os.path.abspath(lpath))
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(base, "lecture.html")

    slides = lesson["slides"]
    html = "".join(build_slide(s, base) for s in slides)

    audio_dir = os.path.join(base, "audio")
    audio = None
    if os.path.isdir(audio_dir):
        clips = [find_audio(audio_dir, n) for n in range(len(slides))]
        if any(clips):
            audio = [b64_audio(p) if p else None for p in clips]

    paper = lesson.get("paper", {})
    cues = None
    cue_path = os.path.join(audio_dir, "cues.json")
    if os.path.exists(cue_path):
        raw = json.load(open(cue_path))
        cues = [raw.get(str(n)) for n in range(len(slides))]

    data = {"narration": [s.get("narration", "") for s in slides],
            "audio": audio, "cues": cues,
            "paper": paper.get("short") or paper.get("title", "this paper")}
    page = (TEMPLATE
            .replace("__TITLE__", esc(paper.get("title", "Lecture")))
            .replace("__PAPER__", esc(paper.get("short", paper.get("title", ""))))
            .replace("__VENUE__", esc(paper.get("venue", "")))
            .replace("__SLIDES__", html)
            .replace("__DATA__", js_json(data)))
    open(out, "w").write(page)
    kb = os.path.getsize(out) // 1024
    subs = sum(len(c) for c in (cues or []) if c)
    print(f"{len(slides)} slides, audio={'inlined' if audio else 'browser voice'}, "
          f"{subs} subtitle cues -> {out} ({kb} KB)")


if __name__ == "__main__":
    main()
