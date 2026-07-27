---
name: paper-lecture
description: Turn a research paper PDF into a narrated, interactive HTML lecture that teaches it, with the paper's own figures extracted and interpreted. Use when the user says "teach me this paper", "make a lecture from this PDF", "explain this paper with slides", or names a PDF and asks to learn it. Not for summarising a paper into text, which needs no tooling.
---

# Paper lecture

You are the model in this pipeline. Python does the mechanical work (pulling figures
out of the PDF, rendering HTML, generating audio) and you do the part no library can:
reading the paper and deciding what a newcomer needs to understand about it.

There are no API keys anywhere. Nothing here calls a model except you.

## Workflow

```bash
# 1. extract. figures land as PNGs, with their captions, plus the full text
python bin/extract.py paper.pdf build/paper

# 2. you read build/paper/text.md and look at the figure PNGs, then write
#    build/paper/lesson.json  (schema below)

# 3. optional audio (macOS only). skip it and the browser narrates instead
python bin/narrate.py build/paper/lesson.json

# 4. render to one self-contained file
python bin/render.py build/paper/lesson.json

# 5. build an Anki deck so it survives past today
python bin/deck.py build/paper/lesson.json
```

Read the figures with the Read tool. They are images and you can see them. Do this
before writing the lesson, because a figure you have not looked at produces narration
that restates its caption, which teaches nothing.

## Writing the lesson

**Aim for 8 to 14 slides.** Fewer and you are summarising, more and it stops being a
sitting.

**Find the load-bearing weakness and build toward it.** Almost every paper has one
joint that carries the whole claim: a sample that cannot support the inference, a
measure that is not what it is named, a between-group comparison standing in for a
within-person process. Locating that is the highest-value thing you do here. Give it
its own slide, late, once the reader has enough to feel the force of it. If a paper
genuinely has no such weakness, say so plainly rather than manufacturing one.

**Quote the paper's own hedges.** Authors usually flag their weakest result somewhere
in the discussion. Readers skip it. Surfacing it is free credibility and free teaching.

**Interpret figures, do not describe them.** `figureNote` should tell the reader where
to look and what the numbers mean. "Autocorrelation doubles from 0.38 to 0.77 across
these two columns" teaches. "Figure 2 shows autocorrelation and variance" does not.

**Write `narration` to be heard, not read.** Short sentences. No parentheses, no
citation numbers, no symbols a voice cannot say: write "n equals 535" and "minus 0.83".
It should complement the slide, not read the bullets back.

**Write `facts` for what should be known cold.** Checks teach understanding
during the lecture; facts are the numbers, definitions and positions worth
holding long term. Six to ten per paper. Every one becomes a card, so each must
stand alone months later: name the paper in the question, since "how many
patients?" is useless on a card. Never duplicate a check as a fact.

**Use `focus` to point at what you are talking about.** One entry per sentence of
narration, in order. As each sentence plays the deck dims the slide and lifts that
one element, and the sentence appears as a subtitle. Targets are `"big"`,
`"point:N"` (zero indexed) and `"figure"`; `null` means dim nothing, which is right
for framing sentences like "Now the problem." Point at the figure exactly when the
narration says to look at it. Getting the sentence count right matters, so generate
the audio first and read `audio/cues.json` to see how your text actually split.

**Make `check` questions test understanding, not recall.** A good one is answerable
from the slide the reader just saw but requires them to do something with it. The
strongest pattern is a counterfactual: "if X were true instead, would this figure look
different?" The `why` field is where the actual teaching happens, so spend words there.
Not every slide needs a check. Four or five across a lecture is right.

**Connect outward.** If the user has related papers, other projects, or their own work
in progress, the last slide should say what this one changes for them specifically.

## lesson.json

```jsonc
{
  "paper": {
    "title": "full title",
    "short": "Author et al. YEAR",     // header, keep it tight
    "venue": "Journal 12(3) 45-67",
    "file": "original.pdf"
  },
  "facts": [                           // optional, becomes Anki cards
    {"q": "atomic question", "a": "the thing to know cold"}
  ],
  "slides": [
    {
      "kicker": "The claim",           // optional, 1-3 words, section label
      "title": "A sentence that asserts something, not a topic label",
      "big": "optional pull quote, one or two sentences, for the key idea",
      "points": ["bullet", "bullet"],  // optional, 3-5, each a complete thought
      "figure": "fig01.png",           // optional, filename from extract.py
      "figureLabel": "Figure 2",
      "figureNote": "where to look and what it means",
      "narration": "the spoken script, 40 to 90 words",
      "focus": [null, "big", "point:2", "figure"],   // optional, one per sentence
      "check": {                       // optional
        "q": "question",
        "a": "short answer",
        "why": "the explanation, this is the teaching"
      }
    }
  ]
}
```

Titles that assert beat titles that label. "Every result here is between people, not
within a person" lands; "Limitations" does not.

## When they come back with questions

The deck collects questions per slide and the reader pastes them back. Treat a
question as evidence about the lesson, not only about the reader. If someone asks
what a term means, the slide used it without earning it. If they ask why a step
follows, the slide asserted instead of arguing. Answer the question first, then say
plainly which slides you would rewrite and offer to rebuild.

## Reasoning effort

Extraction and rendering are mechanical. Authoring the lesson is not: it means holding
a whole argument in view and finding where it bends. If the harness supports raising
reasoning effort, raise it for step 2 and drop it back afterwards.

## Checking your work

Open the rendered HTML and look at it before claiming it is done. Verify every figure
appears (render.py warns on stderr about missing ones) and that no slide is a wall of
text. If `extract.py` missed a figure, the fallback is to crop it yourself with
PyMuPDF at a known rect rather than to write the lecture without it.
