# JACKETEK posts: quality fix report

These are the six posts `01.png` to `06.png`, each 1080 × 1350 PNG. The originals in `export/final_instagram/` are untouched. Script: `tools/quality/fix_quality.py`.

## What caused the pixelation
1. **Posts 01–03, cut-out edges (stickers, polaroids, type, patches).**
   * The only source for these posts is the 3-post grid image (`source/embroidery_reference_posts01-03.webp`), 667 × 888 px per post.
   * The cut-out mask was computed at that size, nearly black-and-white, then enlarged 1.52×. That left 1–2 px stair-steps along edges.
   * Edge pixels kept the old background colour, which shows as light or dark rims on the new background.
   * The light sharpening was applied across those edges, which made the rims stronger.
2. **Post 02, polaroid frames.** The frames' straight edges are ragged in the 667 px source, and the mask copied that raggedness.
3. **Post 03, JK patch.** Its outline was a hard-edged colour mask of the old F patch. That gave an aliased, ragged edge, and slivers of the old navy F patch were left visible next to it.
4. **Posts 04–06** were already rendered from the full-resolution photos at 2× supersampling. Their edges are clean, so they are unchanged here.
5. **Not causes:** JPEG compression (every export is PNG) and the export step itself.

## What was fixed
1. **Posts 01–03:**
   * The mask is recomputed at the final 1080 × 1350 size from the enlarged artwork, within 3 px of the original outline. Nothing new is added.
   * Edge colours are cleaned of the old background, so there are no rims.
   * Sharpening (same strength as before) is now applied to the colour only, not across edges.
   * The removed old dashed guide lines, including a 1 px fringe the old version had left, are kept out of the cut-out.
2. **Post 02:** the outer edges of the three polaroids are replaced by their measured straight edges, drawn at 4× and then reduced. The two stickers on the big print keep their own edges. The big print's bottom edge is mostly hidden under the small prints; that edge is left as it was.
3. **Post 03, JK patch:**
   * The patch is drawn on its measured square, with a smooth, clean outline drawn at 4× and reduced.
   * The square is enlarged 3.4% so it fully covers the old F patch; no navy remnants are left.
   * A soft, restrained contact shadow sits under its new edge, with light from the top left like the design's other shadows.
4. **Not touched:** layouts, text, colours, the background plates, dots, thread and dashed lines. Every change is at cut-out edges, apart from the JK patch area.

## Source assets
* **Replaced or repaired:** none were replaced. The JK patch is still drawn from your file `source/jk_patch_post03.webp`, now with a clean outline.

## Limitations
1. **Posts 01–03 artwork** (photos, stickers, type, the 001 text and others): the only copy is the 667 × 888 px-per-post grid. Edges are now clean, but the detail inside each element cannot be sharper than that file. This needs the original layered file or full-size exports of 01–03.
2. **Background dots and thread (all six posts):** the only source is `source/background_supplied.jpg`, 1280 × 1065 for all six posts, about 425 px per post, enlarged 2.5×. They stay soft. This needs a full-resolution version of the background, about 3240 × 2700.
3. **Small sticker outlines in 01–03** (for example "idk, ChatGPT it."): their white rims are wavy in the source itself; that shape is kept.
