#!/usr/bin/env bash
# Assemble the frames written by record_demo.cjs into the demo MP4 and a short README GIF.
# Usage: docs/demo/make_video.sh <frames dir>
set -euo pipefail
FRAMES="${1:?frames dir}"
OUT="$(cd "$(dirname "$0")" && pwd)"

# MP4 for LinkedIn and the README: 1280x720 H.264, 30 fps, yuv420p so every player accepts it.
ffmpeg -y -loglevel error -f concat -safe 0 -i "$FRAMES/frames.txt" \
  -vf "fps=30,format=yuv420p" -c:v libx264 -preset slow -crf 22 -movflags +faststart \
  "$OUT/ladewueste-demo.mp4"

# GIF: the play-mode part, 960 px wide, 12 fps, with a palette generated from the clip itself.
START="${GIF_START:-16}"; LENGTH="${GIF_LENGTH:-14}"
ffmpeg -y -loglevel error -ss "$START" -t "$LENGTH" -i "$OUT/ladewueste-demo.mp4" \
  -vf "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
  "$OUT/ladewueste-demo.gif"

ls -la "$OUT"/ladewueste-demo.*
