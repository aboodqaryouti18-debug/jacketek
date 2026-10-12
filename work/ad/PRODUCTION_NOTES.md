# JACKETEK — "The thread that tells your story" (44 s, 9:16)

Silent master (no voice-over, no music; audio is added separately).
1080×1920, 24 fps, H.264, 44.0 s. The link to the export is in the final report and in `RENDERS.md`.

## How it is made

| Layer | Made with |
|---|---|
| Jacket motion (opening push-in, 09 sleeve, final pull-back) | Kling 3.0 Pro via Higgsfield, start frames = the original photos on warm beige `#FDF0D5` (`tools/ad/make_frames.py`) |
| Chest, back, two stitching macros | Kling clips from the earlier reel (checked for fidelity) |
| Embroidery-machine sequence | Kling 3.0 Pro text-to-video (burgundy thread on cream, needle stitching) + two earlier macros |
| Colour customisation | **Not AI.** Pixel-accurate recolour of the real front photo (`tools/ad/recolor.py`): only the sleeve leather (+ pocket welts) → Black, then only the body felt → Royal Blue. Both are real configurator options (`jacketportable/.../catalog.ts`). Trims, lettering, patches and snaps keep their original pixels. |
| Construction details (collar, cuff, waistband) | Virtual camera over the real photo |
| The continuous burgundy thread, markers, arrows, transitions | `tools/ad/render.py` (trim-path animation, push transitions that carry the thread across cuts) |
| Arabic copy | Cairo ExtraBold (from the website's font set), shaped with raqm; RTL word-by-word reveal on a warm-beige label, short red `#C1121F` accent |
| Logo finale | Procedural stitch-on: outline first, then satin fill, shaded needle riding the stitching front |

## Timeline

| s | Scene | Copy |
|---|---|---|
| 0.0–3.6 | Jacket alone on warm beige, push-in; thread enters | كل تخرّج إله حچايتَه… |
| 3.6–10 | Thread traces the sleeve → sleeves Black; crosses to the body → body Royal Blue | إنت تختار لون البودي والكمّ… |
| 10–14 | Collar → cuff → waistband markers | وحتى التفاصيل الصغيرة، إلك بيها اختيار. |
| 14–17.4 | Chest lettering | حروفك، اسمك، وتصميم يمثّلك. |
| 17.4–20.8 | Sleeve number 09 | تفاصيلك على الكمّ… |
| 20.8–24.2 | Back, SENIOR 2027 | وخلي الظهر يحچي عنك. |
| 24.2–31.4 | Graphic line lands on the real thread and dissolves into it; four machine macros | مو طباعة… تطريز، غرزة ورا غرزة. |
| 31.4–37.4 | Pull-back to the full front, then the back | كل تفصيلة اخترتها… صارت جزء من حچايتك. |
| 37.4–44.0 | Thread feeds the needle that stitches the logo; slogan | جاكيتك حچايتك |

## Open item: the logo

No logo file was attached (the five attachments are jacket photos), and the website repo has no logo
file either. The finale currently uses an **interim** logo rebuilt from the website's own `Wordmark.tsx`
("J" varsity tag + JACKETEK), which has **no graduation cap**, so it is not the logo described in the brief.
To finish: add the official logo (transparent PNG) and re-render with

```
python3 tools/ad/render.py --clips <clips dir> --logo path/to/logo.png --out jacketek_ad.mp4
```

No new generation is needed; the stitch-on works on any logo image.

## Rebuild

1. `python3 tools/ad/make_frames.py`, `python3 tools/ad/recolor.py`, `python3 tools/ad/make_logo_interim.py`
2. Clips in one folder: `k_open.mp4 k_09.mp4 k_emb1.mp4 k_emb2.mp4 k_reveal.mp4` (this ad) and
   `c2.mp4 c6.mp4 c5b.mp4 c5_v1.mp4` (earlier reel). The Higgsfield job ids are in `RENDERS.md`.
3. `python3 tools/ad/render.py --clips <dir> --out jacketek_ad.mp4` (`--preview` renders with stills only;
   `--frames 12.5,30` writes single PNGs).
