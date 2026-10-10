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
