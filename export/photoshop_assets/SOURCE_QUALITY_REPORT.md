# Source quality report

The canvas is 3240 × 4050 for every post. That is a working size, not a claim of 4K detail everywhere. What each layer actually carries:

## Full detail at 3× (genuine)
* **Background, all posts:**
  * The dots and thread are vectors.
  * The surface colour is a smooth field.
  * The grain is the site's texture asset at 3× native size.
* **Frames (04–06):** vector quads.
* **Type in 04–06:** DARK ExtraBold, set at 600 px and placed at 3×.
* **Jacket photos (04–06):** from `source/new_photos_l/` (back_l, hand_spider, full_jacket_l, chest_l, 09_l: 1185–2000 px).
  * At 3× most of them are shown at about their native size, so detail is real. Some crops are enlarged up to about 1.5×, for example the 09 and the collar crop.
* **JK patch (03):** `source/jk_patch_post03.webp` (2000 × 1778), shown at about native size.
* **Red embroidered words (04–06):** the website embroidery renders, made at 6× the original panel, which is about 2.6 px per 3× pixel.
* **Configurator cards (05):** live-site captures at 3× device pixel ratio.

## Limited by their source
* **Patches in 04–06** (clock, car, LIFE.EXE, cat, BMO): baked at about 820 px wide from the supplied patch images (`source/patches/15–19.jpg`, 384–1200 px).
  * At 3× they are shown at about 1–1.5× their baked size, so they are slightly soft at 100% but clean.
* **Posts 01–03, everything except the JK patch and the background** (photos, stickers, polaroids, headlines, text): the only source is `source/embroidery_reference_posts01-03.webp`, **667 × 888 px per post**.
  * On the 3240 × 4050 canvas this is enlarged **4.56×**, so these layers have clean edges but no real detail beyond that file. No detail was invented.
  * Their lettering is also in `text.svg` as clean traced outlines.
  * **To recover them**, the original design files of posts 01–03 are needed: the layered file, or the original photos, stickers and font.
* **Background surface:** the supplied `source/background_supplied.jpg` is only 1280 × 1065 for all six posts.
  * Its colour field is smooth, so the 3× version is clean.
  * Its dots and thread were redrawn as vectors at their measured positions, colours and sizes, which keeps them sharp.

## Check against the approved posts
Each layer stack, reduced to 1080 × 1350, was compared with `export/quality_fixed/` (`check_all.json`).
* Mean difference per pixel is 2.7 to 5.1 levels out of 255.
* The differences are almost entirely the sharper vector dots and thread, and the crisper type and photo edges.
* Layout, colours and content are the same; see `overview_approved_vs_rebuilt.jpg`.
