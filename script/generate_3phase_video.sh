#!/usr/bin/env bash
set -e

BASE_DIR="$(dirname "$0")/.."
PHASE_DIR="$BASE_DIR/video/3-phase"
OUT_DIR="$PHASE_DIR/video"

mkdir -p "$OUT_DIR"

for d in "$PHASE_DIR"/*/; do
  if [ -f "$d/sketch_group.svg" ]; then
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
    IFS='+' read -r p1 p2 p3 _ <<< "$name"

    in_svg="$d/sketch_group.svg"
    out_mp4="$OUT_DIR/${run_name}.mp4"
    echo "Generating video for: $run_name (p1=\"$p1\", p2=\"$p2\", p3=\"$p3\")"
    python "$BASE_DIR/video/generate_3phase_video.py" \
      "$in_svg" "$out_mp4" --p1 "$p1" --p2 "$p2" --p3 "$p3" --fps 45
  fi
done

echo "Done. Videos are in: $OUT_DIR"