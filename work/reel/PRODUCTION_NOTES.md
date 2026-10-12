# JACKETEK reel — 25 s, 9:16

**Final export (Higgsfield storage, media_id `23b9bb67-6555-472f-bea5-3199713dc5fd`):**
https://d2ol7oe51mr4n9.cloudfront.net/user_3JqR16sxFOdYMNFSTDNLBDaLtQm/23b9bb67-6555-472f-bea5-3199713dc5fd.mp4

MP4, H.264 High + AAC 48 kHz, 1080×1920, 24 fps, 25.000 s, −14.6 LUFS integrated, ~30.6 MB.
Decoded end-to-end without errors. No on-screen text, captions, logos, watermarks or end card.

## Shots

| # | Time (s) | Shot | Source |
|---|---|---|---|
| 1 | 0.0–5.0 | Front, ice-blue studio, slow push-in | Kling 3.0 Pro from `frames/s1_front.png` (job `0c8a7a23…`) |
| 2 | 4.6–7.6 | Chest lettering + collar | Kling 3.0 Pro from `frames/s2_chest.png` (job `e3821611…`) |
| 3 | 7.2–10.2 | Sleeve badge | ffmpeg camera push on `frames/s2_sleeve.png` — Kling refused this frame twice (content filter) |
| 4 | 9.8–13.0 | JK patch macro | Kling 3.0 Pro from `frames/s3_patch.png` (job `9307017a…`) |
| 5 | 12.6–17.6 | Needle stitching macro (+ machine sound) | Kling 3.0 Pro text-to-video (job `fef17cda…`) |
| 6 | 17.2–21.4 | Back, SENIOR 2027 | Kling 3.0 Pro from `frames/s4_back.png` (job `6133b252…`) |
| 7 | 21.0–25.0 | Hero, ice-blue studio | first 2.5 s of Kling job `1d25cd62…` reversed, landing on `frames/s4_hero.png`, then 1.5 s hold |

Every start frame is the original jacket photo (`source/video_refs/`) on a new ice-blue background
or a crop of it (`tools/reel/make_frames.py`). Shot 5 is a generic embroidery macro (grey satin
thread on burgundy wool), not the JK patch being made: the model could not animate the exact
patch convincingly, so it shows the craft without claiming to be the exact production step.
An earlier image-anchored stitching take (job `456fab45…`) was rejected for a smeared needle.

## Audio

* Voice-over: Higgsfield `seed_audio`, preset voice `e2a2d2e6-9ed2-59cd-82af-feaa27f8a678` (Grady),
  21.9 s, starts at 0.6 s. The narration text was sent as written. The dialect and the
  pronunciation of "JACKETEK" have not been checked by a native listener.
* Embroidery-machine sound: native audio of shot 5, low under the voice.
* No music: Higgsfield has no music model for general use.

## Narration

```
تخيّل جاكيت تخرّج معمول على ذوقك… من اللون، للحروف، لكل تفصيلة بالتطريز.
كل اختيار إلك، وكل غرزة إلها حكاية.
من أول خيط، لحد ما تكتمل آخر تفصيلة… فكرتك بتتحوّل لجاكيت حقيقي.
مو بس جاكيت تخرّج… هاي حچايتك.
JACKETEK — جاكيتك حچايتك.
```

## Rebuild

1. `python3 tools/reel/make_frames.py` (needs the cut-outs in `work/reel/cutouts/`, made with rembg `birefnet-general`).
2. Generate the Kling clips; save them as `c1 c2 c4 c5 c6 .mp4` and the hero clip as `c7_kling.mp4`, plus `vo.wav`.
3. `bash tools/reel/prep.sh` (makes `c3.mp4` and `c7.mp4`), then `bash tools/reel/assemble.sh`.
   `VO_START` / `VO_TEMPO` env vars move or speed the voice.
