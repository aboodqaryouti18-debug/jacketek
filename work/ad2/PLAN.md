# JACKETEK product film: inspection report and execution plan (planning only)

No video, image, audio or 3D generation was run for this report. Higgsfield balance was **38.02 credits before and after** the inspection.

---

## A. Verified inventory

### A1. Higgsfield tools (checked through the connected tools and their docs)

| Capability | Tool / model | Verified facts |
|---|---|---|
| Image-anchored video | `kling3_0` | Start + end frame, 3–15 s, std / pro / 4k modes, optional sound. Measured: **8.75 cr** for 5 s pro silent. |
| Reference video | `seedance_2_0` | Image / video / audio refs, start + end frame, 4–15 s, up to 4k. Measured: **45 cr** (1080p, 5 s), **22.5** (720p), **12.5** (fast 720p). |
| Omni-reference, edit, extension | `seedance_2_5` | `t2v`, `omni_reference`, `video_edit` (billed by input length), `video_extension`, 4–30 s, up to 1080p, **480p draft mode**. Measured: **60 cr** (1080p, 5 s). |
| Keyframes + refs | `minimax_h3` (2K) / `minimax_h3_max` | Start / end frame, image / video / audio refs, 4–15 s. Measured: **10 cr** (5 s). |
| Object replacement in a video | `hf_mult_replace_object` (Genjutsu) | Source video + reference images, up to 1080p. |
| Motion transfer / recast | `hf_mult_motion_control`, `motion_control` | |
| Video post | `reframe`, `upscale_video`, `remove_background` (video) | Assumed paid. |
| Image→3D | `generate_3d`, `scene_builder_3d_*` | Exist; quality for garments untested. Paid. |
| Editing / compositing | `video-editing` workflow (**Higgsedit** CLI in the Higgsfield sandbox) | Imports video, cuts, masks / mattes, text, keyframes, 2.5D camera, GLSL, transitions, MP4 / HEVC render. |
| Sandbox | `sandbox_exec` | ffmpeg, Python + Pillow / numpy (raqm Arabic shaping), Playwright / Chromium, 8 CPU. |
| Preflight | `get_cost: true` on generate tools | Documented to return the price without submitting a job. |

Lessons from the earlier attempts (same jacket, same tools):
- Kling kept the lettering legible during **gentle** camera moves from a real start frame.
- Large rotations broke the jacket: in the hero clip the J deformed and the jacket turned.
- Animating stitching altered the K patch's shape within about 4 s.
- The Spider-Man sleeve frame was **refused twice** by the content filter.
- A start + end-frame job sat in the queue for about **70 minutes**.

**Network limitation of this Claude environment.** `upload.higgsfield.ai`, Higgsfield's CDNs (`*.cloudfront.net`, `cdn.higgsfield.ai`) and the embroidery-library storage host are **blocked (HTTP 403)**. Files only reach Higgsfield via a public URL; so far that has meant the public `jacketek` GitHub repo. Finished clips can only be inspected and assembled inside the Higgsfield sandbox. Allow-listing those hosts in the environment's network settings removes this limitation.

### A2. Product references

| What | Path |
|---|---|
| Front 2000×2000 | `jacketek/source/video_refs/jk_front.webp` (= `source/new_photos_l/full_jacket_l.webp`) |
| Back 2000×1131 (SENIOR 2027 artwork, cropped top and bottom) | `jacketek/source/video_refs/jk_back.webp` |
| Chest (Arabic «أنا Strong / بس عيوطة شوي», collar) | `jacketek/source/video_refs/jk_chest.webp` |
| JK patch macro | `jacketek/source/video_refs/jk_patch.webp` |
| Sleeve "09" | `jacketek/source/new_photos_l/09_l.webp` |
| Sleeve Spider-Man patch | `jacketek/source/video_refs/jk_sleeve.webp` |
| Older 2000 px set | `jacketek/source/new_photos/{front,back,collar,sleeve_number,sleeve_patch}.webp` |
| Clean cut-outs | `jacketek/work/reel/cutouts/jk_{front,back}_cut.png` |

### A3. 3D source of truth (new finding)

- **`jacketportable/public/models/fidelio_varsity_v09.glb`** is the current jacket per `src/three/assets.ts`. One mesh with materials Body, Sleeves, Trim, Stripe and Snaps, plus a normal map. Geometry is frozen, from `Fidelio_Varsity_RealisticFit_v09.blend`.
- The website's own embroidery pipeline:
  - `src/three/jacket/EmbroideryDecal.tsx`: projected thread decals with contact shadow.
  - `src/three/embroidery/embroideryMaps.ts`: thread relief maps.
  - `src/three/embroidery/surfacePlacement.ts`: places zones on the real mesh.
  - **`src/three/embroidery/stitchReveal.ts`**: a ready-made "being stitched" reveal, row by row with a serrated front, driven 0→1.
- An earlier, working headless harness that renders the site's embroidery code: `jacketek/tools/embroidery_harness/`.
- To verify: whether the five reference photos were rendered from this GLB. They look like CGI renders on a beige wall.

### A4. Logo

- **No official logo file was found.** None of the attachments is a logo, and the website has no logo file (the `Wordmark.tsx` component draws a "J" tag plus JACKETEK in code).
- Embroidered **JACKETEK wordmark** images in the brand design spec: `jacketportable/jacketek-design-spec.zip` → `assets/embroidery/jacketek-wordmark-{burgundy,sand,ecru,silver}@2x.webp`. The silver one is also at `public/assets/embroidery/`. They're wordmarks only; I saw no graduation cap.
- `jacketek/work/ad/logo/logo_interim.png` was built by me from code. **It is not official and must not be used as "the logo".**

### A5. Embroidery library

- Catalogue: `jacketportable/runtime-assets/embroidery-library/library.json`. It lists **1,866 designs in 42 libraries**, with zone metadata. File names are only numbers (`1.PNG`…).
- **The artwork is not in Git**; it is git-ignored on purpose. It lives on the owner's computers ("portable folder") and on remote storage that this environment cannot reach. So **I could not see any real library design.**
- What I could see: the tracked **test subset**. These are original JACKETEK designs drawn by `scripts/embroidery-fixtures/build.mjs` from the site's own fonts: "Class of 2027" banner, "27" numeral, star crest, varsity "A", "2027", "SENIORS". There are also site-owned back elements in `public/assets/embroidery/back/{crest,banner,motto,script,star}.png`.
- Licensing: `LICENSED_ASSETS_README.md` and `src/features/configurator/library/README.md` say the library is the **third-party OJISAN import**. It contains licensed-character collections and must **not** be distributed or published **until the licensing is confirmed in writing**.

Libraries by zone (from the catalogue):

| Zone | Usable candidates (rights still to confirm) | Exclude (characters / brands / logos / likeness) |
|---|---|---|
| Main back | **AQ مكتبة تصميمات الظهر** (76, the only `mainBack` library); site-owned crest / banner / motto / script; fixture "Class of 2027" | — |
| Left chest | **F الحروف الامامية** (20 front-letter styles, with letter templates A–Z); fixture varsity monogram | — |
| Shoulder / number | **BC الارقام** (24); fixture "27" | — |
| Other sleeve | AB باتش الدفعة (15), AU نجوم وسماء (28), AC تاج (16), AI فراشات (20), Y الورد (64), AG عبارات (124) | A DC & Marvel, B Disney, C Hello Kitty, U Conan, AD Anime, AE SpongeBob, AF Cartoon characters, AH Powerpuff, AO Lilo & Stitch, AP My Little Pony, AV Harry Potter, AX Adventure Time, AY One Piece, Z Clubs, AN Players, I Cars (likely marques), N Currencies |

⚠️ **The reference jacket itself carries a Marvel Spider-Man patch** (`jk_sleeve.webp`). Featuring it in a commercial is a rights risk, and Higgsfield's filter already blocks it.

### A6. Earlier outputs (for reference only)

- Generated clips and prompts: `jacketek/work/reel/PRODUCTION_NOTES.md`, `jacketek/work/ad/RENDERS.md` (job IDs; files are stored on Higgsfield).
- Renderer and tooling: `jacketek/tools/ad/`, `jacketek/tools/reel/`.

---

## B. Storyboard (about 40 s, 9:16, 24 fps; warm beige studio, one key light from upper left throughout)

| # | Time | Picture | Camera | Thread | Text |
|---|---|---|---|---|---|
| 1 | 0–4 | Jacket on an invisible form, ¾ front, centred | Slow dolly-in plus 10° arc right | A single burgundy thread drifts in from the top-left edge, passes **in front of** the chest, then curls behind the left sleeve | «إنت تختار» (small, low third, fades out) |
| 2 | 4–9 | Left shoulder / "09" | Continuous arc left 50°, push in to the shoulder | The thread wraps behind the arm and re-emerges at the 09 | «تفاصيلك» |
|   |      | **Options:** the 09 zone briefly shows 2 alternatives from **BC الارقام** as real decals on the sleeve, then settles back to the original 09 | | The thread tightens as each option settles | |
| 3 | 9–15 | Around the side to the **back** (SENIOR 2027) | Arc continues to a straight-on back, slight rise | The thread runs across the shoulder blades and frames the back artwork | «تطريزك» |
|   |      | **Options:** 2 alternatives from **AQ** or the site-owned back set, then the original | | | |
| 4 | 15–21 | Around the other side to the **chest** (JK + Arabic), passing the **other sleeve** | Arc completes to a ¾ front; brief push to the left chest | The thread loops behind the collar and lands on the JK | — |
|   |      | **Options:** chest letter styles from **F**; other sleeve per the decision in F | | | |
| 5 | 21–22 | Hidden transition | Camera follows the thread upward off the collar; the thread fills the frame (match on the thread) | The 3D thread becomes the machine's upper thread | — |
| 6 | 22–30 | **Embroidery machine**: the back panel of the same jacket hooped under the needle, SENIOR 2027 being stitched | 3 angles: wide machine head (2.5 s), mid on the lettering (3 s), macro satin stitches (2.5 s) | The real upper thread feeds the needle | «حچايتك» |
| 7 | 30–35 | Finished jacket, full, back → ¾ front | Pull-back plus slow orbit | The thread slides off the shoulder and out of frame | — |
| 8 | 35–40 | **Official logo** embroidered on warm beige felt | Macro push-in, gentle settle | The thread enters, feeds the last stitches of the logo and stops | «جاكيتك حچايتك» (hold 1.5 s) |

Rules: one continuous virtual camera for shots 1–5 and 7 (a single path); hidden cuts only at 5→6 and 6→7; no arrows, outlines, glows or UI.

---

## C. Sourcing the embroidery options from the real library

1. **You confirm usage rights** for the libraries to be shown in an advert (OJISAN licence). Until then, only the original JACKETEK fixtures and site-owned back elements are safe.
2. **You copy the chosen designs' artwork** from your portable folder (`runtime-assets/embroidery-library/assets/<designId>/full.webp`). It can't be fetched from here, and must **not** go into the public `jacketek` repo.
3. **I list candidate design IDs per zone** from `library.json` (AQ, F, BC, plus sleeve libraries) for you to pick 2–3 each. I can't judge the artwork until I see it.
4. The options are shown the way the website shows them: through the site's own decal and thread-relief code on the jacket's real zones (`surfacePlacement.ts`). They change on the jacket itself, never as pop-up panels.

---

## D. Embroidery-machine scene with the exact back design

**Why not generate it:** none of the available video models takes an exact artwork constraint. In our own tests, stitching prompts reshaped lettering within seconds. «SENIOR 2027» plus the cap would drift.

**Recommended options, most reliable first:**

1. **Real footage (best).** Film your own industrial machine stitching the actual back design file on burgundy wool (phone, 4K vertical, locked-off plus macro; the 3 angles of shot 6). It is exact and authentic, and we cut it in with the thread match. Needs the original back artwork or digitized file (e.g. DST) and a short shoot.
2. **Composite (no shoot).** A machine "plate" with the hoop over **plain, unembroidered burgundy wool**, from stock footage or 1–2 locked-off Kling clips (8.75 cr each). The **exact back artwork** goes onto the hoop plane with the site's `stitchReveal` shader logic, tracked to the fabric. A needle and foot layer is masked in front, and the thread is matched.
   - For the artwork, best is the original design file. Fallback: extract it from `jk_back.webp`, whose lighting and perspective are baked in and whose top and bottom are cropped.
3. **Not recommended:** asking a model to animate stitching of that exact text.

---

## E. Recommended workflow

| Step | Method | Automatable | Credits |
|---|---|---|---|
| 1 | Collect missing inputs (G4 list in H) | You | 0 |
| 2 | **Fidelity test:** render the GLB with the reference colours and embroidery (JK, Arabic chest text, 09, back art, patch) at the 5 reference angles; compare with the photos | Yes, local three.js / Playwright | 0 |
| 3 | Camera path + **3D burgundy thread** (spline tube with twist normal, true occlusion in front of and behind the jacket) + option decal swaps; render shots 1–5 and 7 frame by frame | Yes, local | 0 |
| 4 | Machine scene: real footage (option 1) or composite (option 2) | Shoot: you. Composite: yes | 0, or ~9–18 for plates |
| 5 | Logo scene from the **official file**, stitch reveal on beige felt, Cairo ExtraBold line | Yes, local | 0 |
| 6 | Minimal Arabic text (4 words + slogan) | Yes | 0 |
| 7 | Assembly + grade + export (ffmpeg or Higgsedit) | Yes | 0 |
| 8 | *Optional* AI realism pass on short segments (e.g. Seedance `video_edit` 480p draft first) | Only after a free test and your approval | Paid |

Separate tools or methods needed: the real-footage shoot; licence confirmation; possibly a Blender / Cycles render if the three.js realism isn't premium enough. Blender is not installed here, and installing it is unverified.

---

## F. Technical risks

1. **Jacket identity:** the GLB may differ from the reference photos (proportions, materials, wool and leather look). Step 2 checks this before anything else.
2. **Exact lettering:** the Arabic chest text, JK, 09 and the back art must be rebuilt as decals from exact sources (fonts and settings, or the original artwork). Any AI pass risks drift.
3. **Photorealism:** a WebGL render may read as CGI. Mitigations: the site's realism lighting, depth of field, grain, motion blur; a Cycles render if available; a short, approved AI pass.
4. **Thread continuity:** easy inside the 3D shots; at 5→6 and 6→7 it depends on matching the real or plate thread position.
5. **Camera motion:** AI clips deform on big orbits, so the orbit must be 3D-rendered.
6. **Licensing:** the Spider-Man patch on the hero jacket; OJISAN library rights; never push licensed artwork to the public repo.
7. **Infrastructure:** blocked Higgsfield and storage hosts; a 38-credit budget (about 4 Kling-pro clips); Kling queue delays of up to an hour; the content filter.

---

## G. Credit-safety checklist

**Consume credits (never run without your explicit OK):** `generate_video` / `_batch`, `generate_image` / `_batch`, `generate_audio` / `_batch`, `execute_preset`, Marketing Studio / Ads Studio / Shorts Studio generation, AI-influencer generation, `upscale_image` / `upscale_video`, `reframe`, `outpaint_image`, `remove_background`, relight, `motion_control`, Genjutsu models, `generate_3d`, `scene_builder_3d_generate_*`, dubbing / voice change, `virality_predictor`, `video_analysis_create`. Anything unlisted counts as paid until verified.

**Verified or documented as safe (no generation):**
- Read-only lookups: `models_explore`, `get_workflow_instructions` and bundle files, `balance`, `list_*`, `jobs_wait` / status.
- File transfer: `media_upload` / `media_import_url` / `media_confirm`. The balance arithmetic of the earlier runs matched the jobs only.
- **`sandbox_exec`:** hours of rendering left the balance exactly at 81.77 − 5 × 8.75 = 38.02.
- `get_cost: true` preflight (documented "without submitting").
- All local work in this environment: Python, ffmpeg, Playwright / three.js, git.

---

## H. Proposed next step (not executed)

**A free, local fidelity test.** Load `fidelio_varsity_v09.glb` in the existing embroidery harness with the reference colours and the jacket's embroidery. Render 5 stills at the reference angles (front, back, chest, 09 sleeve, other sleeve) and give you a side-by-side against the photos. **0 credits.**

To prepare it, please send or confirm:
1. The **official logo** file (PNG / SVG). Is the embroidered JACKETEK wordmark in the design spec it, or is there a version with a graduation cap?
2. The **original back artwork** (and, ideally, the configuration of the chest text, JK, 09 and patch), or confirmation to extract it from the photos.
3. Whether the reference photos came from this GLB or the website's renders.
4. Licence status of the OJISAN library for advertising use, and which libraries you allow.
5. What to do with the **Spider-Man patch** in the commercial: keep, avoid close-ups, or show the other sleeve with a licence-safe design.
6. Whether a **real machine-footage shoot** is possible (preferred for scene 6).
7. Optionally: allow-list the Higgsfield upload and CDN hosts in this environment's network settings.
