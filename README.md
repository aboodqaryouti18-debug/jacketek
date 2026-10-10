# JACKETEK — Instagram background treatment (POST 04 / 05 / 06)

Recreates the reference background in `source/taatheer el background.webp`:
very faint thin vertical lines plus a soft, diffused depth centred in **each**
post (it restarts per post) and fading out toward all four edges.

* Beige posts (04, 06): soft centre shadow-depth, about −5.5% at the very centre.
* Navy post (05): soft centre glow, about +16% at the centre.
* Background lines are about 18% more visible in the centre of each post and unchanged at the edges (`LINE_CENTER` / `LINE_EDGE`).
* Only brightness changes; hue and chroma stay the same, so beige, navy and red stay on brand.
* Photos, frames, embroidery and type are masked out, so only the background changes.

## Files
| Path | What |
|---|---|
| `export/layers_1080x1350/` | **Editable layers** for the real 1080×1350 source files |
| `export/posts/POST_0X_background.png` | Each post with the treatment applied (preview resolution) |
| `export/grid/grid_preview_background.png` | Updated three-post grid preview |
| `export/grid/grid_before_after.jpg` | Before (top) / after (bottom) |
| `tools/background_treatment.py` | Generator script. All strengths are in `SETTINGS` |

## Using the layers in the source files
The layers are 16-bit greyscale PNGs. Put them directly above each post's background layer, below the photos and type:

* `*_depth_multiply.png`: blend **Multiply** (beige centre depth)
* `*_depth_colordodge.png`: blend **Color Dodge** (navy centre glow)
* `*_lines_multiply.png`: blend **Multiply** (line cores)
* `*_lines_colordodge.png`: blend **Color Dodge** (line highlights)

To make the effect stronger or weaker, change layer opacity, or edit `SETTINGS` and re-run:
`python3 tools/background_treatment.py` (needs only numpy and Pillow).

## Red-word embroidery (POST 04 / 05 / 06)
Raised red-thread satin embroidery on **only** «ذكرياتك» (04), «تفصيلة» (05) and «معنى» (06).
The stitch style follows `source/embroidery_reference_posts01-03.webp`.

* Script: `tools/embroider_words.py` (needs numpy, opencv-python-headless, Pillow).
  Input `export/posts/POST_0X_background.png`, output `export/posts/POST_0X_embroidered.png`
  and `export/grid/grid_preview_embroidered.png`.
* `work/embroidery/` holds each word's masks: `mask_hard` is the letter pixels, `mask_alpha` the soft edges.
  It also holds the stitch-direction map and a 4× close-up render of each word.
* Settings at the top of the script: `STITCH_SLANT_DEG`, `THREAD_PITCH`, `THREAD_CONTRAST`,
  `RELIEF`, `FRAY`, `SHADOW`. Word boxes are in `WORDS`.
* The red full stops after the words are deliberately left flat, as in the reference.
* `export/grid/embroidery_review_sheet.jpg` shows the reference next to before/after close-ups of each word.

## Website 3D embroidery on the red words (POST 04 / 05 / 06)
This replaces the earlier `tools/embroider_words.py` look. It uses the JACKETEK website's own 3D embroidery code, unchanged, from the `jacketportable` repo.

* **Masks:** the posts' words are DARK ExtraBold (verified by `tools/website_embroidery/fit_dark.py`: 97–99% overlap at a uniform scale, every mismatch on the anti-aliased outline). Each word is re-set in the site's own `DARK-ExtraBold.ttf` at 6× post resolution, at the fitted position.
* **Render:** `tools/embroidery_harness/` is a small Vite page. It imports the site's `createLetteringEmbroidery` (`embroideryMaps.ts`), `EmbroideryDecal.tsx` and `StudioLighting.tsx`, with NeutralToneMapping, on a flat surface seen straight on. Thread and shadow are rendered as separate layers.
* **Colour:** dyed to brand crimson #C1121F with the site's `ThreadDyes.tsx` formula (luminance × colour ÷ mean luminance).
* **Composite:** onto `export/posts/POST_0X_background.png`, which is untouched. Other red elements (the full stops and details elsewhere) keep their original pixels.
* **Run:** `cd tools/embroidery_harness && node_modules/.bin/vite --config vite.config.mjs`, then `python3 tools/website_embroidery/run_pipeline.py`. `node_modules` is a symlink to `jacketportable/node_modules` after `npm ci` there.
* **Outputs:** `export/website_embroidery/` (three posts, the grid, the comparison sheet, `report.json`). Intermediates are in `work/website_embroidery/` (masks, the site's five maps per word, renders, post-resolution layers, live-site captures).
* **Live-site comparison:** `tools/website_embroidery/capture_site.mjs` captures the real configurator (Red thread, Lalezar, left chest).
