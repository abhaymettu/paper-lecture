#!/usr/bin/env bash
# Fetch the Kokoro-82M ONNX weights used by narrate.py --engine kokoro.
# About 340 MB, once. Set KOKORO_MODEL_DIR to put them somewhere else.
set -euo pipefail
DIR="${KOKORO_MODEL_DIR:-$HOME/.cache/paper-lecture}"
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
mkdir -p "$DIR"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ -s "$DIR/$f" ]; then
    echo "have $f"
  else
    echo "fetching $f ..."
    curl -fL --progress-bar -o "$DIR/$f" "$BASE/$f"
  fi
done
echo "weights in $DIR"
