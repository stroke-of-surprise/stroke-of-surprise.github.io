#!/usr/bin/env bash
set -e

BASE_DIR="$(dirname "$0")/.."
OPT_DIR="$BASE_DIR/video/optimization"
OUT_DIR="$OPT_DIR/video"

mkdir -p "$OUT_DIR"

for d in "$OPT_DIR"/*/; do
  # Skip the video output directory itself
  if [ "$(basename "$d")" = "video" ]; then
    continue
  fi

  if [ -d "$d/group_images" ]; then
    run_name="$(basename "$d")"
    name="$run_name"

    # Strip leading "(number)" prefix, e.g. "(1)pig+angel-25" -> "pig+angel-25"
    if [[ "$name" =~ ^\([0-9]+\)(.+)$ ]]; then
      name="${BASH_REMATCH[1]}"
    fi

    # Strip trailing "-number" suffix, e.g. "pig+angel-25" -> "pig+angel"
    if [[ "$name" =~ ^(.+)-[0-9]+$ ]]; then
      name="${BASH_REMATCH[1]}"
    fi

    # Split into p1 and p2 by "+"
    IFS='+' read -r p1 p2 _ <<< "$name"

    out_mp4="$OUT_DIR/${run_name}.mp4"
    echo "Generating optimization video for: $run_name (p1=\"$p1\", p2=\"$p2\")"
    
    python3 "$BASE_DIR/video/generate_optimization_video.py" \
      "$d" -o "$out_mp4" --fps 10 --hold 2.0 \
      --p1 "$p1" --p2 "$p2"
  fi
done

echo "Done. Videos are in: $OUT_DIR"

