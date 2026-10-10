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

## Rebuilt posts at 1080×1350 (POST 04 / 05 / 06)
`export/rebuild_1080x1350/POST_0X.png`: the approved posts (`export/patches/`, unchanged) rebuilt from their separate elements at the final Instagram size. No flattened post is upscaled or sharpened.

* **Geometry.** The grid preview shows the centre 3:4 of each 4:5 post. Panel px map to post px as `x' = 33 + 1.5203·x`, `y' = 1.5203·y`. The 33 px side strips are background; the hairlines and dashed guides continue into them.
* **Measured on the original grid** (`tools/rebuild/`):
  * `fit_text.py`: every text run re-set in DARK ExtraBold by the browser (`text_runs.py` holds the exact strings) and fitted.
  * `measure_frames.py` + `refine_windows.py`: every print as a quadrilateral, both the outer frame and the photo window.
  * `measure_dashes.py` + `dash_model.py`: the dashed guides as arcs, period 17.75 px, dash 9.1 × 1.8 px. Stretches the design knocks out behind the type stay hidden.
  * `shadow_fit.py`: the design's own print shadows, a two-term model per colour world.
* **Sources:**
  * The 2000 px jacket photos (`source/new_photos`) and the JK chest render.
  * The two POST_05 configurator cards, re-captured from the live site in Arabic at 3× (`capture_cards.mjs`, `cards_fit.py`): Body step with leather; Embroidery step with 4 zones (JK / 27 / 09 / 09, cut out of the renders by `thumb_cutouts.py`).
  * The website 3D embroidery renders of the red words (6×).
  * The baked embroidered patches (~4×).
* **Background:** `compose.py` re-runs the hairlines, the earlier print shadows and the website world (site grain tile at ~1:1) directly at 1080×1350.
* **Run:** start the site (`npx vite` in jacketportable, port 5173) and the embroidery harness (port 5199). Then run `capture_cards.mjs work/rebuild/site`, `cards_fit.py`, `fit_text.py`, `measure_frames.py`, `refine_windows.py`, `dash_model.py`, `shadow_fit.py`, then `compose.py`, `review.py` and `verify_text.py`.
* **Review:** `compare_POST_0X.jpg` shows the approved post (enlarged) next to the rebuild. `work/rebuild/crops_POST_0X.png` holds 100% crops. `report_text.json` holds the text overlap per run.
* **Known differences from the approved posts:**
  * The live site's panels have moved by a few px since the cards were made, so some card rows sit 1–2 px off.
  * The card 1 capture is blanked below the swatches, where the original card is empty.
  * The hard shadow step under the frames in the approved posts (from an over-wide text guard) is now a continuous shadow.

## Posts 01–03 background on posts 04–06 (`export/reference_bg_1080x1350/`)
The rebuilt posts with the reference grid's background finish (`source/embroidery_reference_posts01-03.webp`). They keep their own colour order on purpose: 01–03 are navy–beige–navy, 04–06 are **beige–navy–beige**.

* **Measurement** (`tools/rebuild/ref_background_fit.py` → `work/rebuild/ref_background.json`):
  * Reference navy: flat (0, 46, 71); its light varies by under 1%.
  * Reference beige: peak (254, 242, 217), with an elliptical fall-off (top corners 94%) and a floor fall-off from 68% of the height (bottom corners 84%). Fitted to 1.5 levels RMS on clean background pixels.
* **Render:** `python3 tools/rebuild/compose.py --reference-bg` → `work/rebuild/stage_reference_bg/`. This swaps the website world (glow, window light, vignette) for the reference colour and light. It keeps the faint hairlines, the print shadows and the dashed guides, and adds the site grain at 45% strength.
* **Unchanged:** photos, cards, type, red-word embroidery and patches are the same layers as `export/rebuild_1080x1350/`. The patches read their light from the approved composite, so they are identical too; inside every photo and card, 0 pixels changed.
* **Review:** `python3 tools/rebuild/review_reference_bg.py`.
  * `grid_with_reference.jpg`: 01–03 above 04–06, as on the profile.
  * `compare_POST_0X.jpg`: before | after.
  * `work/rebuild/crops_refbg_POST_0X.png`: 100% crops.

## Posts 01–03 with the striped background of posts 04–06 (`export/posts01-03_striped_1080x1350/`)
The direction is 04–06 → 01–03. Posts 01–03 keep navy–beige–navy; posts 04–06 (`export/rebuild_1080x1350/`) are unchanged in beige–navy–beige.

* **Source:** the only copy of posts 01–03 is the grid `source/embroidery_reference_posts01-03.webp` (667 × 888 per post). It is never overwritten.
* **Script:** `tools/posts0103/compose0103.py`.
  * It splits each panel against its plain old background into a foreground matte (photos, patches, type, dashes, logos; solid prints filled) and a shade layer (the design's own shadows).
  * It renders the 04–06 striped background (`tools/rebuild/compose.py`: hairlines, website world, site grain) at 1080 × 1350 for each post's colour.
  * It recombines: background × shade + foreground.
  * The foreground is upscaled 1.52× with Lanczos, plus a light 35% unsharp mask. No AI and no invented detail.
* **Outputs:**
  * `POST_01–03.png`
  * `compare_POST_0X.jpg` (original | new)
  * `profile_grid_01-06.jpg`
  * The mattes and shade layers are in `work/posts0103/`.
