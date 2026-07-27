#!/usr/bin/env python3
"""Pre-render each slide's narration to audio with the macOS `say` command.

Usage: narrate.py <lesson.json> [--voice NAME] [--rate WPM]

Writes <lesson dir>/audio/NN.m4a, which render.py picks up automatically.
Skip this entirely and the deck narrates with the browser's built-in voice,
which costs nothing and needs no files. Use this when you want the nicer
macOS voices, or an offline deck that sounds the same on every machine.

macOS only: `say` and `afconvert` both ship with the OS.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

# Best-sounding stock voices, in order. Premium variants need a one-time
# download in System Settings > Accessibility > Spoken Content.
PREFERRED = ["Ava (Premium)", "Serena (Premium)", "Zoe (Premium)", "Ava", "Samantha", "Daniel"]


def available_voices():
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    return [line.split("  ")[0].strip() for line in out.splitlines() if line.strip()]


def pick_voice(requested):
    voices = available_voices()
    if requested:
        if requested not in voices:
            sys.exit(f"voice {requested!r} not installed. Try: say -v '?'")
        return requested
    for v in PREFERRED:
        if v in voices:
            return v
    return voices[0] if voices else sys.exit("no voices found")


def main():
    if sys.platform != "darwin":
        sys.exit("narrate.py needs macOS `say`. On other platforms skip it and "
                 "let the deck use the browser voice.")
    for tool in ("say", "afconvert"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")

    ap = argparse.ArgumentParser()
    ap.add_argument("lesson")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--rate", type=int, default=180, help="words per minute")
    args = ap.parse_args()

    lesson = json.load(open(args.lesson))
    base = os.path.dirname(os.path.abspath(args.lesson))
    out = os.path.join(base, "audio")
    os.makedirs(out, exist_ok=True)

    voice = pick_voice(args.voice)
    print(f"voice: {voice} at {args.rate} wpm")

    for n, slide in enumerate(lesson["slides"]):
        text = slide.get("narration", "").strip()
        if not text:
            continue
        aiff = os.path.join(out, f"{n:02d}.aiff")
        m4a = os.path.join(out, f"{n:02d}.m4a")
        subprocess.run(["say", "-v", voice, "-r", str(args.rate), "-o", aiff, text], check=True)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", aiff, m4a],
                       check=True, capture_output=True)
        os.remove(aiff)
        kb = os.path.getsize(m4a) // 1024
        print(f"  {n:02d}.m4a  {kb:>4} KB  {text[:60]}...")

    print(f"\ndone. re-run render.py to inline the audio.")


if __name__ == "__main__":
    main()
