#!/usr/bin/env python3
"""Validate a lesson before you render it.

Usage: check.py <lesson.json> [more.json ...]

Everything here fails silently otherwise: a mistyped figure filename drops the
image with a warning nobody reads, a focus array one entry too long points at a
sentence that does not exist, and a focus target naming a bullet the slide does
not have simply never highlights. All three produce a lecture that looks fine
and teaches less than it should.

Exits non-zero if anything is wrong, so it can gate a build.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narrate import sentences  # same splitter the cue generator uses

MAX_POINTS = 6
MAX_NARRATION_WORDS = 120


def targets_for(slide):
    t = {"big"} if slide.get("big") else set()
    t |= {f"point:{i}" for i in range(len(slide.get("points", [])))}
    if slide.get("figure"):
        t.add("figure")
    return t


def check(path):
    problems, warnings = [], []
    try:
        lesson = json.load(open(path))
    except json.JSONDecodeError as e:
        return [f"not valid JSON: {e}"], []
    base = os.path.dirname(os.path.abspath(path))

    if not lesson.get("slides"):
        problems.append("no slides")
        return problems, warnings
    if not lesson.get("paper", {}).get("short"):
        warnings.append("paper.short missing, the header will be empty")

    for i, s in enumerate(lesson["slides"]):
        at = f"slide {i}"
        if not s.get("title"):
            problems.append(f"{at}: no title")
        if not s.get("narration", "").strip():
            warnings.append(f"{at}: no narration, so no audio and no subtitles")

        if s.get("figure"):
            if not os.path.exists(os.path.join(base, s["figure"])):
                problems.append(f"{at}: figure {s['figure']!r} not found next to the lesson")
            elif not s.get("figureNote"):
                warnings.append(f"{at}: figure with no figureNote, so it is shown without "
                                "being interpreted")

        n_sent = len(sentences(s.get("narration", "")))
        focus = s.get("focus", [])
        if focus:
            if len(focus) > n_sent:
                problems.append(f"{at}: {len(focus)} focus entries but narration splits into "
                                f"{n_sent} sentences, so the last {len(focus)-n_sent} never fire")
            elif len(focus) < n_sent:
                warnings.append(f"{at}: {len(focus)} focus entries for {n_sent} sentences, "
                                f"the last {n_sent-len(focus)} will not highlight")
            avail = targets_for(s)
            for j, f in enumerate(focus):
                if f is not None and f not in avail:
                    problems.append(f"{at}: focus[{j}] = {f!r} does not exist on this slide "
                                    f"(has {sorted(avail) or 'nothing targetable'})")

        if len(s.get("points", [])) > MAX_POINTS:
            warnings.append(f"{at}: {len(s['points'])} bullets, more than {MAX_POINTS} is a wall")
        words = len(s.get("narration", "").split())
        if words > MAX_NARRATION_WORDS:
            warnings.append(f"{at}: narration is {words} words, long for one slide")

        c = s.get("check")
        if c and not all(c.get(k) for k in ("q", "a")):
            problems.append(f"{at}: check needs both q and a")

    for j, f in enumerate(lesson.get("facts", [])):
        if not (f.get("q") and f.get("a")):
            problems.append(f"fact {j}: needs both q and a")

    seen = set()
    for f in lesson.get("facts", []):
        if f.get("q") in seen:
            warnings.append(f"duplicate fact question: {f['q'][:60]!r}")
        seen.add(f.get("q"))

    return problems, warnings


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: check.py <lesson.json> [more.json ...]")
    bad = 0
    for path in sys.argv[1:]:
        problems, warnings = check(path)
        name = os.path.relpath(path)
        if not problems and not warnings:
            print(f"ok    {name}")
            continue
        print(f"{'FAIL' if problems else 'warn'}  {name}")
        for p in problems:
            print(f"        error: {p}")
        for w in warnings:
            print(f"        warn:  {w}")
        bad += bool(problems)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
