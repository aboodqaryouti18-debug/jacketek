# JACKETEK: Photoshop assets for posts 01–06

Each folder (`01` … `06`) holds one post, taken apart into aligned layers on a **3240 × 4050 px** canvas (3× the 1080 × 1350 Instagram size), sRGB, 8-bit.

## Assembling a post in Photoshop
1. **File > New:** 3240 × 4050 px, 72 ppi, RGB 8-bit, sRGB.
2. **Place the layers in file-name order** (`00_…`, `01_…`, …), which is back to front.
   * Use **File > Place Embedded**, or drag all PNGs in at once.
   * Every PNG is a full-canvas 3240 × 4050 layer, so each one lands exactly in place. Keep X = 0, Y = 0, scale 100%, rotation 0.
   * If Photoshop scales placed files, turn off *Preferences > General > Resize Image During Place*.
3. **Blend modes:** all layers are **Normal, 100%**.
   * Shadow layers are black with the shadow in their transparency. Their strength is editable with Opacity, and the shadow with Gaussian Blur or Move.
   * The `content_bbox` of every layer in `layout.json` gives where its pixels are, if you want to crop it.
4. **Type:** `text.svg` holds the lettering as clean vector outlines, in the exact positions.
   * **Posts 04–06:** the font is **DARK ExtraBold** (`jacketportable/public/assets/fonts/dark/DARK-ExtraBold.ttf`). The hidden group `type_editable` in `text.svg` also has the lines as live text, so you can retype a line in the same font. Align it to the outline; positions are approximate.
   * **Posts 01–03:** that font file isn't available, so the outlines are traced from the post.
   * The PNG text layers are the lettering exactly as approved.
   * To use the SVG, File > Place it on top. It has the same 3240 × 4050 viewBox, so it lands in place.
5. **Background:** `00_background.png` is the full opaque background (surface, dots and thread). `background_dots_thread.svg` holds the dots and thread as vectors at the same coordinates, if you want to restyle them.
6. **Instagram file:** Image > Image Size to 1080 × 1350 px (33.333%), resample Bicubic (automatic), then File > Export > PNG. `final_1080x1350.png` in each folder is exactly this result.

## Contents of each folder
| File | What |
|---|---|
| `00_background.png` | Background only (opaque): navy or beige surface, every visible dot, the connecting thread |
| `NN_shadow_*.png` | Separate shadow layers (prints, patches, embroidery, the design's own soft shadows) |
| `NN_frame_*.png` | Polaroid or card frames (04–06) |
| `NN_photo_*.png`, `NN_card_*.png` | Each photo or configurator screenshot on its own, cut to its frame window (04–06) |
| `NN_text_*.png` | Each line of type on its own |
| `NN_embroidery_*.png` | The red embroidered words |
| `NN_patch_*.png` | Each embroidered patch |
| `NN_sticker_*.png`, `NN_polaroid_*.png`, `NN_headline_*.png` | Posts 01–03: each sticker, print and headline on its own |
| `NN_fragment_*.png` | Tiny leftovers from the source (a few px); delete freely |
| `text.svg` | Type as vector outlines (plus editable text, 04–06) |
| `background_dots_thread.svg` | Dots and thread as vectors |
| `layout.json` | Canvas, every layer (file, type, x, y, width, height, content box, rotation, scale, order, source) and the check against the approved post |
| `preview_3240x4050.png` | All layers stacked, as Photoshop will show them |
| `final_1080x1350.png` | That preview reduced to the Instagram size |
| `compare_approved_vs_rebuilt.jpg` | Approved post (left) next to the rebuilt one (right) |

In this folder: `SOURCE_QUALITY_REPORT.md`, `check_all.json`, `overview_rebuilt_from_layers.jpg` and `overview_approved_vs_rebuilt.jpg`.
The approved posts are in `export/quality_fixed/` and are untouched.
Scripts: `tools/psd_assets/` (`stage_a_patch_tone.py`, `dot_grid_fit.py`, `background_vector.py`, `export_assets.py`).
