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


def b64_audio(path):
    mime = "audio/mp4" if path.endswith(".m4a") else "audio/aiff"
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
  .check.open button{display:none}
  .check .ans b{color:var(--ok)}
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
  .big{background:var(--card);border:1px solid var(--line);border-radius:10px;
       padding:1.2rem 1.3rem;margin:0 0 1.4rem;box-shadow:var(--shadow)}
  .big p{margin:0}
  @media (max-width:640px){ main{padding:1.2rem .9rem 6rem} h2{font-size:1.3rem} }
  @media (prefers-reduced-motion:reduce){ *{animation:none!important;transition:none!important} }
</style></head><body>
<header><b>__PAPER__</b><span>__VENUE__</span></header>
<div id="bar"><div></div></div>
<main id="deck">__SLIDES__</main>
<footer>
  <button id="prev">&larr;</button>
  <button id="next">&rarr;</button>
  <button id="say">▶ Narrate</button>
  <span class="sp"></span>
  <span class="hint">&larr;&rarr; move · space narrate · enter reveal · click figure to zoom</span>
  <span id="pos"></span>
</footer>
<div id="zoom"><img alt=""></div>
<script>
const DATA = __DATA__;
const deck = document.getElementById('deck');
const slides = [...deck.querySelectorAll('.slide')];
let i = 0, audio = null;

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
function narrate(){
  const t = DATA.narration[i];
  if (!t) return;
  if (audio || speechSynthesis.speaking){ stop(); return; }
  document.getElementById('say').textContent = '■ Stop';
  if (DATA.audio && DATA.audio[i]){
    audio = new Audio(DATA.audio[i]);
    audio.onended = () => { audio = null; document.getElementById('say').textContent = '▶ Narrate'; };
    audio.play();
  } else {
    const u = new SpeechSynthesisUtterance(t);
    u.rate = 1.0;
    // ponytail: browser voice by default. narrate.py pre-renders nicer audio if you want it.
    const v = speechSynthesis.getVoices().find(v => /Samantha|Ava|Serena|Daniel/.test(v.name));
    if (v) u.voice = v;
    u.onend = () => { document.getElementById('say').textContent = '▶ Narrate'; };
    speechSynthesis.speak(u);
  }
}
document.getElementById('prev').onclick = () => show(i - 1);
document.getElementById('next').onclick = () => show(i + 1);
document.getElementById('say').onclick = narrate;
document.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') show(i + 1);
  else if (e.key === 'ArrowLeft') show(i - 1);
  else if (e.key === ' '){ e.preventDefault(); narrate(); }
  else if (e.key === 'Enter'){
    const c = slides[i].querySelector('.check');
    if (c) c.classList.add('open');
  }
  else if (e.key === 'Escape') document.getElementById('zoom').classList.remove('on');
});
deck.addEventListener('click', e => {
  if (e.target.tagName === 'IMG'){
    const z = document.getElementById('zoom');
    z.querySelector('img').src = e.target.src;
    z.classList.add('on');
  }
  if (e.target.dataset.reveal) e.target.closest('.check').classList.add('open');
});
document.getElementById('zoom').onclick = e => e.currentTarget.classList.remove('on');
show(0);
</script></body></html>"""


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_slide(s, figdir):
    out = ['<section class="slide">']
    if s.get("kicker"):
        out.append(f'<div class="kicker">{esc(s["kicker"])}</div>')
    out.append(f'<h2>{esc(s["title"])}</h2>')
    if s.get("big"):
        out.append(f'<div class="big"><p>{esc(s["big"])}</p></div>')
    if s.get("points"):
        out.append("<ul>" + "".join(f"<li>{esc(p)}</li>" for p in s["points"]) + "</ul>")
    if s.get("figure"):
        path = os.path.join(figdir, s["figure"])
        if os.path.exists(path):
            cap = f'<b>{esc(s.get("figureLabel", "Figure"))}.</b> {esc(s.get("figureNote", ""))}'
            out.append(f'<figure><img alt="{esc(s.get("figureLabel",""))}" '
                       f'src="{b64_png(path)}"><figcaption>{cap}</figcaption></figure>')
        else:
            print(f"  warning: missing figure {s['figure']}", file=sys.stderr)
    if s.get("check"):
        c = s["check"]
        out.append(
            '<div class="check"><p>' + esc(c["q"]) + "</p>"
            '<button data-reveal="1">Show answer</button>'
            '<div class="ans"><p><b>' + esc(c["a"]) + "</b></p>"
            + (f"<p>{esc(c['why'])}</p>" if c.get("why") else "")
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
        clips = []
        for n in range(len(slides)):
            p = os.path.join(audio_dir, f"{n:02d}.m4a")
            clips.append(b64_audio(p) if os.path.exists(p) else None)
        if any(clips):
            audio = clips

    data = {"narration": [s.get("narration", "") for s in slides], "audio": audio}
    paper = lesson.get("paper", {})
    page = (TEMPLATE
            .replace("__TITLE__", esc(paper.get("title", "Lecture")))
            .replace("__PAPER__", esc(paper.get("short", paper.get("title", ""))))
            .replace("__VENUE__", esc(paper.get("venue", "")))
            .replace("__SLIDES__", html)
            .replace("__DATA__", json.dumps(data)))
    open(out, "w").write(page)
    kb = os.path.getsize(out) // 1024
    print(f"{len(slides)} slides, audio={'inlined' if audio else 'browser voice'} -> {out} ({kb} KB)")


if __name__ == "__main__":
    main()
