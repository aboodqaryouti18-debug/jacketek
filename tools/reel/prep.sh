#!/usr/bin/env bash
# Prepare the two shots that are not used straight from Kling.
#   c3.mp4 sleeve detail: Kling refused this frame twice (content filter on the
#          sleeve badge), so it is a slow camera push on the real photo instead.
#   c7.mp4 hero: the first 2.5 s of the Kling hero clip played in reverse
#          (camera glides in and lands exactly on the real hero frame), then
#          1.5 s hold on that frame with a barely perceptible push.
# Inputs in the cwd: s2_sleeve.png, s4_hero.png, c7_kling.mp4
set -euo pipefail

# 5 s @ 24 fps push from 100% to 108% toward the badge (render at 2x to avoid
# zoompan stair-stepping, then downscale).
ffmpeg -y -hide_banner -loglevel error -loop 1 -i s2_sleeve.png -t 5 -filter_complex \
  "scale=2160:3840,zoompan=z='1+0.08*on/120':x='iw*0.63-iw/zoom*0.63':y='ih*0.5-ih/zoom/2':d=120:s=2160x3840:fps=24,scale=1080:1920:flags=lanczos,format=yuv420p" \
  -c:v libx264 -crf 14 -preset slow c3.mp4

ffmpeg -y -hide_banner -loglevel error -i c7_kling.mp4 -t 2.5 -vf "reverse,fps=24,format=yuv420p" -an \
  -c:v libx264 -crf 14 -preset slow hero_a.mp4
ffmpeg -y -hide_banner -loglevel error -loop 1 -i s4_hero.png -t 1.5 -filter_complex \
  "scale=2160:3840,zoompan=z='1+0.012*on/36':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=36:s=2160x3840:fps=24,scale=1080:1920:flags=lanczos,format=yuv420p" \
  -c:v libx264 -crf 14 -preset slow hero_b.mp4
ffmpeg -y -hide_banner -loglevel error -i hero_a.mp4 -i hero_b.mp4 \
  -filter_complex "[0:v][1:v]concat=n=2:v=1[v]" -map "[v]" -c:v libx264 -crf 14 -preset slow c7.mp4
