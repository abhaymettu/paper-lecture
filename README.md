# paper-lecture

Turn a research paper into a narrated, interactive lecture that actually teaches it,
using Claude Code as the model. No API keys, no external services, no per-paper cost
beyond the Claude Code session you are already in.

The output is one self-contained HTML file: the paper's real figures, cropped from the
PDF and interpreted rather than described, narration you can play, and questions that
make you commit to an answer before revealing it.

## Why this exists

There are good open-source tools that turn a PDF into slides. Microsoft's
[ResearchStudio](https://github.com/microsoft/ResearchStudio) does it well and produces
video too. They all share a shape: a pipeline that calls a hosted model, with the
model's job being layout and summary.

This one inverts that. The Python here is deliberately dumb, doing only what is
mechanical: find the figures, render the HTML, generate the audio. The judgement lives
in a skill file that Claude Code reads. That means:

- **No API keys.** The only model involved is the one already running your session.
- **The teaching is the point.** Any tool will put Figure 2 on a slide. The skill tells
  the model to find the joint where the paper's claim actually bends, build toward it,
  and quiz you on whether you saw it.

## Install

```bash
git clone https://github.com/abhaymettu/paper-lecture
cd paper-lecture
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ln -s "$PWD/skills/paper-lecture" ~/.claude/skills/paper-lecture
```

For narration, the deck falls back to your browser's speech synthesis with nothing
installed at all. For a voice you would actually listen to, fetch the Kokoro weights
once:

```bash
bin/get-kokoro.sh    # ~340 MB, local, no torch, no API
```

macOS `say` is the third option (`--engine say`). Its stock voices sound like a screen
reader; the Premium voices under System Settings > Accessibility > Spoken Content are
much better and `narrate.py` picks them up automatically once installed.

## Use

In Claude Code:

```
teach me build/papers/12_vandeLeemput_2014.pdf
```

Or by hand:

```bash
.venv/bin/python bin/extract.py paper.pdf build/paper   # figures + text
# ... Claude reads them and writes build/paper/lesson.json ...
.venv/bin/python bin/narrate.py build/paper/lesson.json # optional, macOS
.venv/bin/python bin/render.py build/paper/lesson.json  # -> lecture.html
```

Open `lecture.html`. Arrow keys move, space plays and pauses the narration, CC
toggles subtitles, click a figure to zoom. Keyboard shortcuts stand down while you
are typing an answer.

While narration plays, each spoken sentence appears as a subtitle and the slide dims
everything except the thing that sentence is about. Timings are real: `narrate.py`
synthesises a sentence at a time and records each duration, rather than estimating.

Stuck on a slide, press `?`. The question is saved with the slide it came from, and
"Copy questions" puts the lot on your clipboard as a prompt you paste back to Claude.
A static page cannot answer you; this at least stops the question evaporating.

Answers stay locked until you type an attempt. Recognising a correct answer feels like
knowing it and builds little memory; producing one, even wrongly, is what sticks.

## How the figure extraction works

The naive approach is to pull embedded images out of the PDF, which in journal articles
gives you dozens of disconnected vector fragments per figure. The next approach is to
find caption text and crop above it, which breaks the moment you hit a journal that puts
captions beside or below the artwork. PNAS does both in the same paper.

So `extract.py` clusters all the non-text ink on a page, filters out page furniture
(rules, watermarks, the repository stamp down the margin), and gives each caption its
nearest cluster. Direction never enters into it.

## Layout

```
bin/extract.py    PDF  -> figNN.png + captions + text.md
bin/check.py      lint a lesson before rendering it
bin/narrate.py    lesson.json -> audio/NN.m4a        (macOS `say`)
bin/render.py     lesson.json -> one self-contained lecture.html
bin/deck.py       lesson.json -> .apkg for Anki (FSRS does the scheduling)
skills/           the Claude Code skill: how to author a lesson
examples/         a finished lesson.json to read
```

`lesson.json` is the interface between the two halves. Everything above it is Claude's
judgement; everything below it is deterministic.

## Tests

```bash
python tests/test_caption_match.py       # caption detection on real paper strings
python tests/test_check.py               # the linter catches what it claims to
python tests/test_render_escaping.py     # no HTML or script injection from a lesson
python tests/test_pipeline.py <pdf-dir>  # extract -> lint -> render -> deck, every PDF
```

The last one is the useful one. It synthesises a lesson from whatever each PDF
yields and pushes it through the whole pipeline, so publisher layouts you have
never hand-tested still get exercised.

## Note on papers

Papers are copyrighted. `.gitignore` keeps PDFs, extracted figures, and rendered decks
out of the repo, and you should keep it that way. The example ships as a `lesson.json`
only, which is original prose about a paper rather than any part of the paper itself.

## License

MIT. See [LICENSE](LICENSE).
