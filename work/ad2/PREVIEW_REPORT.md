# JACKETEK ad: free local 3D validation (Phases 1–3)

**No Higgsfield tool was called in this phase**: no generation, upscaling or any other Higgsfield operation.
The last balance reading was 38.02 credits (end of the planning phase). All work below ran locally in this environment.

## Outputs

| What | Path |
|---|---|
| Five-view contact sheet | `work/ad2/phase1_views/contact_sheet.jpg` |
| Renders vs reference photos | `work/ad2/phase1_views/compare_render_vs_reference.jpg` |
| Material close-up, render vs photo | `work/ad2/phase1_views/material_compare_front.jpg` |
| Individual views (1080×1350) | `work/ad2/phase1_views/0{1..5}_*.png`, `close_front.png`, `close_back.png` |
| Orbit + thread preview (540×960, 24 fps, 12 s) | `work/ad2/phase2_orbit/orbit_thread_preview.mp4` |
| Orbit contact sheet | `work/ad2/phase2_orbit/orbit_sheet.jpg` |
| Preview code (isolated) | `work/ad2/preview3d/` |

## Method and commands

- **Isolated folder** `work/ad2/preview3d/` with its own `package.json`: three 0.170.0, @react-three/fiber 8.18.0,
  @react-three/drei 9.122.0, React 18.3.1, Vite 5.4.21, @vitejs/plugin-react 4.7.0 (the website lockfile's versions),
  plus playwright-core 1.56.1. Installed with `npm install` from the npm registry (free).
- The page (`main.tsx`) imports the **website's own code read-only** from the `jacketportable` clone:
  - `@/three/jacket/JacketModel` → `GltfJacket`, which applies zone tinting and keeps the GLB's own textures;
  - `@/three/stage/StudioLighting`;
  - NeutralToneMapping, as in `ThreeJacketViewer.tsx`;
  - the site's studio cream `#FCF0D6` (from `heroLayout.ts`) as background.
  The GLB is served read-only from `jacketportable/public/models/fidelio_varsity_v09.glb`.
- Appearance uses **real configurator colours** closest to the reference: Burgundy felt `#64152B` for the body and rib,
  White leather `#F1F0E8` for the sleeves and stripes, silver snaps, relaxed fit. No embroidery (see Phase 1, finding 1).
- Rendering: local headless Chromium (`/opt/pw-browsers/chromium-1194`), SwiftShader WebGL. Encoding: local ffmpeg.
  - `cd work/ad2/preview3d && npm install`
  - `node render_views.mjs ../phase1_views` (five views; close-ups with `DIST=1.75 TARGET_Y=0.45 VIEWS='[["close_front",0],["close_back",180]]'`)
  - `node render_orbit.mjs ../phase2_orbit 12 540 960` (orbit; resumable)
- Network: the scripts log every host the page contacts. Only `127.0.0.1:5299` (the local Vite server) was contacted.
- Website untouched: `git status` in `jacketportable` is clean, and nothing was written there (no `node_modules` either).

## Phase 1: does the 3D jacket match the references?

**Matches (same model):** silhouette and proportions; set-in sleeve shape; rib collar with two cream stripes; striped cuffs
and waistband; angled pocket welts; snap placket and snap count; hem and drape.

**Differences:**
1. **Embroidery is missing entirely.** The GLB carries no embroidery, and the reference jacket's design (JK chest letters,
   Arabic «أنا Strong / بس عيوطة شوي», sleeve "09", back «SENIOR / SENIOR / SENIOR 2027» with cap, Spider-Man sleeve patch)
   is **not stored anywhere in the repository**: no saved design, order or configuration. The site can render embroidery
   (`EmbroideryLayer` / `EmbroideryDecal`), but it needs that configuration and the library artwork, which isn't available here.
2. **Material realism is far below the photos.** In the photos the wool shows fibre and felting, the leather has grain and soft
   sheen, and yoke seams and topstitching are visible. The real-time render is smooth and evenly lit, and reads as CG. The GLB has a
   single normal map; the photos were clearly made with a higher-fidelity renderer or texture set than the website's WebGL viewer.
3. **Sleeve colour and lighting:** the render's sleeves read whiter (the site's three-light studio + tone mapping); the photos are
   softer, warmer and more directional.
4. **Camera:** the renders use the site's product camera (FOV 24°, 7° pitch). The photos are close to that at the front; the
   reference back photo is a tighter, slightly lower, cropped view.

**Verdict:** the model is the right basis for **geometry, camera and thread** work. As final-quality pixels it is **not** ready:
the embroidery must be supplied, and the surface quality must come up to the photos' level.

## Phase 2: orbit and thread

- One continuous camera path: yaw −20° → 200° (front → side → back), constant 2.75 m distance, FOV 24°, eased in and out,
  jacket centred throughout. No cuts.
- The thread is a real 1.6 mm tube in the same 3D scene (`thread.tsx`): a slow descending spiral of about 1.7 turns around the
  jacket. A moving window along it (head plus trailing length) leads the camera.

Findings:
- **Occlusion and depth: correct.** The thread passes in front of the chest and sleeves and disappears behind the body and
  re-emerges, purely from the depth buffer. No compositing is needed, and the effect is physically consistent.
- **Camera motion: smooth.** Constant distance, centred jacket, no jumps.
- **Thread visibility: weak in front of the burgundy body.** Same colour family, and only ~2 px at 540 px width. It reads well
  against the beige and the white sleeves.
- **Thread realism: too clean.** A perfectly smooth geometric spiral reads as a drawn line: no sag, no slight wobble, no visible
  twist, no thickness variation.
- **Thread timing: wrong in the second half.** By the time the camera reaches the back (~8.5–12 s), the visible stretch of
  thread has spiralled down and mostly behind the jacket. Only small fragments show at the sides, so the thread "leaves"
  exactly when the back is revealed. The path and window must be timed to the camera, e.g. head always slightly ahead
  of the camera's view direction and at chest height.
- **Lighting during the orbit:** the back views are lit more flatly and darker than the front (the key light is fixed to the
  studio).
- Preview: 288 frames, 540×960, 24 fps, 12.0 s; decodes cleanly; the only host contacted was `127.0.0.1:5299`.

## Problems to fix before the full advertisement

1. **Embroidery source (blocker).** We need either the original design configuration (texts, fonts, sizes, positions, and the
   library images: JK style, 09 numerals, back artwork, Spider-Man patch artwork) or permission to rebuild the decals from the
   reference photos (exact pixels, but with lighting baked in).
2. **Surface realism (blocker for a "premium photoreal" film).** Options, all still free unless noted:
   - a higher-quality local render: Blender/Cycles with the GLB plus fabric/leather detail maps. Blender isn't installed here; a
     download/installation would be needed (free, but larger);
   - find the source used for the reference photos (the `.blend` named in `assets.ts`, `Fidelio_Varsity_RealisticFit_v09.blend`,
     is not in this repo);
   - later and paid: an AI realism pass on short segments, only with your approval.
3. **Thread look and timing:** keep the thread's head ahead of the camera and at chest height through the back reveal; add a gentle sag/wobble and a subtle twist normal, slightly brighter burgundy or rim light so it reads on the
   burgundy body, and route it so it crosses the sleeves and background more than the body.
4. **Lighting:** a light rig that moves with the orbit, or a stronger rim/back light, so the back stays as attractive as the front.
5. **Render speed:** software WebGL takes ~4–5 s per 540×960 frame here; a 40 s 1080×1920 film would take hours locally.
   Acceptable for a final render, slow for iteration.

## Recommended next step (not started)

Decide the embroidery and realism sources (problems 1 and 2). Then, still free and local: improve the thread (problem 3) and the
lighting (problem 4), and render a short 1080×1920 test of the front→side→back move with the embroidery in place.
