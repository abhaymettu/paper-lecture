#!/usr/bin/env python3
"""Pre-render each slide's narration to audio.

Usage: narrate.py <lesson.json> [--engine auto|kokoro|say] [--voice V] [--speed S]

Writes <lesson dir>/audio/NN.m4a, which render.py picks up automatically.
Skip this step entirely and the deck narrates with the browser's built-in voice,
which costs nothing and needs no files.

Engines, best first:

  kokoro  Kokoro-82M, a small neural TTS running locally through onnxruntime.
          No torch, no API, no network once the weights are cached. This is the
          one that does not sound like a screen reader.
              pip install kokoro-onnx soundfile
              bin/get-kokoro.sh          # ~340 MB of weights, one time

  say     The macOS built-in. Free and always there, but the stock voices are
          rough. macOS ships better ones on request: System Settings >
          Accessibility > Spoken Content > System Voice > Manage Voices, then
          download a Premium voice such as Ava or Zoe. This script prefers those
          automatically once they exist.
"""
import argparse
import json
import re
import os
import shutil
import subprocess
import sys

MODEL_DIR = os.environ.get("KOKORO_MODEL_DIR", os.path.expanduser("~/.cache/paper-lecture"))
MODEL = os.path.join(MODEL_DIR, "kokoro-v1.0.onnx")
VOICES = os.path.join(MODEL_DIR, "voices-v1.0.bin")

KOKORO_DEFAULT = "af_heart"
# Stock macOS voices are rough; the Premium downloads are markedly better.
SAY_PREFERRED = ["Ava (Premium)", "Zoe (Premium)", "Serena (Premium)", "Evan (Enhanced)",
                 "Ava", "Samantha", "Daniel"]


def kokoro_ready():
    if not (os.path.exists(MODEL) and os.path.exists(VOICES)):
        return False
    try:
        import kokoro_onnx, soundfile  # noqa: F401
        return True
    except ImportError:
        return False


def to_m4a(wav, m4a):
    """Shrink to m4a when afconvert is around, otherwise keep the wav."""
    if shutil.which("afconvert"):
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", wav, m4a],
                       check=True, capture_output=True)
        os.remove(wav)
        return m4a
    return wav


def sentences(text):
    """Split narration for subtitling. Narration is written to be spoken, so
    plain end-punctuation splitting is enough; no abbreviation handling needed."""
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"“])', text.strip())
    return [p.strip() for p in parts if p.strip()]


def synth_kokoro(texts, out, voice, speed):
    """Synthesise a sentence at a time so each caption gets a real timestamp,
    then join the clips into one file per slide."""
    import numpy as np
    import soundfile as sf
    from kokoro_onnx import Kokoro

    k = Kokoro(MODEL, VOICES)
    if voice not in k.get_voices():
        sys.exit(f"voice {voice!r} unknown. Available: {', '.join(sorted(k.get_voices()))}")
    print(f"engine: kokoro   voice: {voice}   speed: {speed}")

    made, cues = [], {}
    for n, text, focus in texts:
        chunks, marks, t = [], [], 0.0
        for s in sentences(text):
            samples, rate = k.create(s, voice=voice, speed=speed, lang="en-us")
            dur = len(samples) / rate
            marks.append({"t": round(t, 3), "d": round(dur, 3), "s": s,
                          "f": focus[len(marks)] if len(marks) < len(focus) else None})
            chunks.append(samples)
            t += dur
        joined = np.concatenate(chunks) if chunks else np.zeros(1)
        wav = os.path.join(out, f"{n:02d}.wav")
        sf.write(wav, joined, rate)
        cues[n] = marks
        made.append((n, to_m4a(wav, os.path.join(out, f"{n:02d}.m4a")), text))

    json.dump(cues, open(os.path.join(out, "cues.json"), "w"))
    return made


def synth_say(texts, out, voice, speed):
    if sys.platform != "darwin":
        sys.exit("the `say` engine needs macOS. Install kokoro-onnx instead, or skip "
                 "narrate.py and let the deck use the browser voice.")
    listing = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    installed = [ln.split("  ")[0].strip() for ln in listing.splitlines() if ln.strip()]
    if voice and voice not in installed:
        sys.exit(f"voice {voice!r} not installed. Try: say -v '?'")
    if not voice:
        voice = next((v for v in SAY_PREFERRED if v in installed), installed[0])
        if "Premium" not in voice and "Enhanced" not in voice:
            print("note: no Premium or Enhanced voice installed, so this will sound "
                  "robotic.\n      System Settings > Accessibility > Spoken Content > "
                  "System Voice > Manage Voices\n      Or install kokoro-onnx, which "
                  "sounds better than any of them.\n")
    rate = int(180 * speed)
    print(f"engine: say   voice: {voice}   rate: {rate} wpm")
    made = []
    for n, text, _focus in texts:
        aiff = os.path.join(out, f"{n:02d}.aiff")
        subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", aiff, text], check=True)
        made.append((n, to_m4a(aiff, os.path.join(out, f"{n:02d}.m4a")), text))
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson")
    ap.add_argument("--engine", choices=["auto", "kokoro", "say"], default="auto")
    ap.add_argument("--voice", default=None,
                    help="kokoro: af_heart, am_michael, bf_emma ... | say: Ava (Premium)")
    ap.add_argument("--speed", type=float, default=1.0)
    args = ap.parse_args()

    lesson = json.load(open(args.lesson))
    base = os.path.dirname(os.path.abspath(args.lesson))
    out = os.path.join(base, "audio")
    os.makedirs(out, exist_ok=True)

    texts = [(n, s["narration"].strip(), s.get("focus", []))
             for n, s in enumerate(lesson["slides"]) if s.get("narration", "").strip()]
    if not texts:
        sys.exit("no narration in this lesson")

    engine = args.engine
    if engine == "auto":
        engine = "kokoro" if kokoro_ready() else "say"
    if engine == "kokoro" and not kokoro_ready():
        sys.exit(f"kokoro not ready. pip install kokoro-onnx soundfile, then "
                 f"bin/get-kokoro.sh (looked in {MODEL_DIR})")

    if engine == "kokoro":
        made = synth_kokoro(texts, out, args.voice or KOKORO_DEFAULT, args.speed)
    else:
        made = synth_say(texts, out, args.voice, args.speed)

    for n, path, text in made:
        print(f"  {os.path.basename(path):<10} {os.path.getsize(path)//1024:>4} KB  {text[:56]}...")
    print("\ndone. re-run render.py to inline the audio.")


if __name__ == "__main__":
    main()
