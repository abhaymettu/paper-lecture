#!/usr/bin/env python3
"""Build a real Anki deck (.apkg) from one or more lessons.

Usage: deck.py <lesson.json> [more.json ...] [-o out.apkg] [--name "Deck name"]

The lecture builds understanding once. Keeping it is a scheduling problem, and
that problem is solved: Anki has shipped FSRS as its built-in scheduler since
2023, it is open source, it syncs, and it has a phone app you will actually
open on a bus. Writing another scheduler would be strictly worse.

So this produces a deck and gets out of the way. Double-click the .apkg.

Cards come from:
  - every `check` in the lesson, which is already a retrieval question
  - every entry in the optional `facts` list, for things worth knowing cold
Figures ride along on the cards whose slide had one.
"""
import argparse
import hashlib
import json
import os
import sys

try:
    import genanki
except ImportError:
    sys.exit("needs genanki:  pip install genanki")


def stable_id(text):
    """Deterministic ids so re-importing updates cards instead of duplicating."""
    return int(hashlib.sha1(text.encode()).hexdigest()[:8], 16)


MODEL = genanki.Model(
    stable_id("paper-lecture/model/v1"),
    "Paper lecture",
    fields=[{"name": "Front"}, {"name": "Back"}, {"name": "Figure"}, {"name": "Source"}],
    templates=[{
        "name": "Recall",
        "qfmt": "{{Front}}",
        # Answer first, then the figure, then where it came from.
        "afmt": '{{FrontSide}}<hr id="answer">{{Back}}'
                '{{#Figure}}<br><br>{{Figure}}{{/Figure}}'
                '<br><br><span class="src">{{Source}}</span>',
    }],
    css="""
.card { font-family: Georgia, serif; font-size: 19px; line-height: 1.55;
        text-align: left; color: #1a1a1a; background: #faf8f5; padding: 1.2em; }
.nightMode .card { color: #e8e6e3; background: #14161a; }
b { color: #2c6e49; }
.nightMode b { color: #7fb069; }
img { max-width: 100%; border-radius: 4px; }
.src { font-family: system-ui, sans-serif; font-size: 13px; opacity: .55; }
hr#answer { border: none; border-top: 1px solid #ccc; margin: 1em 0; }
""")


def cards_from(lesson, lesson_dir, media):
    paper = lesson.get("paper", {})
    short = paper.get("short", "paper")
    tag = short.replace(" ", "-").replace(".", "").replace(",", "")
    out = []

    for slide in lesson["slides"]:
        c = slide.get("check")
        if not c:
            continue
        back = f"<b>{c['a']}</b>"
        if c.get("why"):
            back += f"<br><br>{c['why']}"

        fig = ""
        if slide.get("figure"):
            path = os.path.join(lesson_dir, slide["figure"])
            if os.path.exists(path):
                # Namespace the filename: Anki's media folder is global.
                name = f"{tag}-{slide['figure']}"
                dest = os.path.join(lesson_dir, name)
                if not os.path.exists(dest):
                    with open(path, "rb") as a, open(dest, "wb") as b:
                        b.write(a.read())
                media.append(dest)
                fig = f'<img src="{name}">'

        out.append((c["q"], back, fig, short, [tag, "check"]))

    for f in lesson.get("facts", []):
        out.append((f["q"], f["a"], "", short, [tag, "fact"]))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lessons", nargs="+")
    ap.add_argument("-o", "--out", default=None)
    ap.add_argument("--name", default=None, help="Anki deck name")
    args = ap.parse_args()

    media, rows = [], []
    for path in args.lessons:
        lesson = json.load(open(path))
        rows += cards_from(lesson, os.path.dirname(os.path.abspath(path)), media)

    if not rows:
        sys.exit("no checks or facts in these lessons, nothing to build")

    name = args.name or (
        json.load(open(args.lessons[0])).get("paper", {}).get("short", "Papers")
        if len(args.lessons) == 1 else "Papers")
    deck = genanki.Deck(stable_id("paper-lecture/deck/" + name), name)

    for front, back, fig, src, tags in rows:
        deck.add_note(genanki.Note(model=MODEL, fields=[front, back, fig, src],
                                   tags=tags, guid=genanki.guid_for(front)))

    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(args.lessons[0])),
        name.replace(" ", "-").replace(".", "") + ".apkg")
    genanki.Package(deck, media_files=media).write_to_file(out)

    checks = sum(1 for r in rows if "check" in r[4])
    print(f"{len(rows)} cards ({checks} checks, {len(rows) - checks} facts), "
          f"{len(media)} figures -> {out}")
    print("Double-click it to import. Anki schedules with FSRS by default.")


if __name__ == "__main__":
    main()
