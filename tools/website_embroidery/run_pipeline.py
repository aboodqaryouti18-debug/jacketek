"""Posts 04-06: the website's 3D embroidery on the three red words.

  1. DARK masks at K x post resolution (placement from dark_fit.json)
  2. the harness renders them with the site's own code
     (createLetteringEmbroidery + EmbroideryDecal + StudioLighting)
  3. composite onto the posts (separate outputs; inputs untouched)

Needs the harness dev server running:
  cd tools/embroidery_harness && node_modules/.bin/vite --config vite.config.mjs
Usage: python3 tools/website_embroidery/run_pipeline.py [--thread #C1121F] [--stage masks|render|composite|all]
"""
import argparse
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "work" / "website_embroidery"
HARNESS = ROOT / "tools" / "embroidery_harness"
K = 6                     # mask/render resolution, x post pixels
WORDS = {"POST_04": "ذكرياتك", "POST_05": "تفصيلة", "POST_06": "معنى"}
CRIMSON = (0xC1, 0x12, 0x1F)  # brand crimson (src/styles/index.css --brand-crimson 193 18 31) = the posts' red
# Rendered in the site's default light thread, then dyed crimson exactly as
# src/components/ThreadDyes.tsx dyes the site's silver embroidery renders.
RENDER_THREAD = "#ECE7DC"


def stroke_px(alpha8):
    """The site's strokeWidth() (textArtwork.ts): 2 x area / outline length."""
    a = alpha8 >= 128
    inner = a[1:-1, 1:-1]
    edge = inner & ~(a[1:-1, :-2] & a[1:-1, 2:] & a[:-2, 1:-1] & a[2:, 1:-1])
    return 2 * inner.sum() / max(edge.sum(), 1)


def harness(tasks):
    f = W / "tasks.json"
    f.write_text(json.dumps(tasks, ensure_ascii=False))
    subprocess.run(["node", str(HARNESS / "render.mjs"), str(f)], check=True, cwd=HARNESS)


def stage_masks():
    fits = {r["name"]: r for r in json.loads((W / "dark_fit.json").read_text())}
    tasks, meta = [], {}
    for name, word in WORDS.items():
        r = fits[name]
        s = (r["sx"] + r["sy"]) / 2
        px = 600 * s * K
        pad = round(px * 0.18)            # room for the cast shadow; keeps every texture <= 2048 px wide like the site
        out = W / "masks" / f"{name}_mask_x{K}.png"
        tasks.append(dict(op="mask", text=word, px=px, pad=pad, out=str(out)))
        meta[name] = dict(px=px, pad=pad)
    harness(tasks)
    for name in WORDS:
        a = cv2.imread(str(W / "masks" / f"{name}_mask_x{K}.png"), cv2.IMREAD_UNCHANGED)[..., 3]
        meta[name]["strokePx"] = float(stroke_px(a))
        meta[name]["size"] = list(a.shape[::-1])
    (W / "masks" / "meta.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


def stage_render(thread):
    meta = json.loads((W / "masks" / "meta.json").read_text())
    harness([dict(op="embroider", mask=str(W / "masks" / f"{n}_mask_x{K}.png"), strokePx=m["strokePx"],
                  threadHex=thread, layer=layer, outDir=str(W / "render" / n))
             for n, m in meta.items() for layer in ("thread", "shadow")])


POSTS = ROOT / "export" / "posts"
OUT = ROOT / "export" / "website_embroidery"


def read_rgba(p):
    a = cv2.imread(str(p), cv2.IMREAD_UNCHANGED).astype(np.float64) / 255
    return np.dstack([a[..., 2], a[..., 1], a[..., 0], a[..., 3]])


def dye(rgba):
    """ThreadDyes.tsx: luminance x colour / mean luminance (sRGB), so the
    rendered shading, sheen and ridges stay and the mean lands on the colour."""
    lum = rgba[..., :3] @ np.array([0.2126, 0.7152, 0.0722])
    solid = cv2.erode((rgba[..., 3] > 0.99).astype(np.uint8), np.ones((9, 9))) > 0
    mean = lum[solid].mean()
    col = np.array(CRIMSON, np.float64) / 255
    return np.clip(lum[..., None] * col / mean, 0, 1), mean


def to_post(img, M, shape):
    """Mask/render pixels -> post pixels: warp onto a K x post grid, then
    area-average down (no information is invented)."""
    MK = M.copy()
    MK[:, :] *= K
    big = cv2.warpAffine(img, MK, (shape[1] * K, shape[0] * K), flags=cv2.INTER_LINEAR, borderValue=0)
    return cv2.resize(big, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)


def stage_composite():
    fits = {r["name"]: r for r in json.loads((W / "dark_fit.json").read_text())}
    meta = json.loads((W / "masks" / "meta.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    report, posts = {}, []
    for name in WORDS:
        f, m = fits[name], meta[name]
        k = 600 / m["px"]
        # mask px -> DARK600 px -> post px (dark_fit.json; the fit masks had pad 40)
        M = np.array([[f["sx"] * k, 0, f["tx"] + f["sx"] * (40 - m["pad"] * k)],
                      [0, f["sy"] * k, f["ty"] + f["sy"] * (40 - m["pad"] * k)]])
        post = cv2.cvtColor(cv2.imread(str(POSTS / f"{name}_background.png")), cv2.COLOR_BGR2RGB).astype(np.float64) / 255
        H, Wd = post.shape[:2]
        thread = read_rgba(W / "render" / name / "render_thread.png")
        shadow = read_rgba(W / "render" / name / "render_shadow.png")
        dyed, mean = dye(thread)
        # premultiplied layers -> post resolution
        t_a = to_post(thread[..., 3], M, (H, Wd))
        t_rgb = to_post(dyed * thread[..., 3:4], M, (H, Wd))
        s_a = to_post(shadow[..., 3], M, (H, Wd))
        # the old flat letters: replaced by the background under them
        old = cv2.imread(str(ROOT / "work" / "embroidery" / f"{name}_mask_hard.png"), 0) > 0
        zone = cv2.dilate(old.astype(np.uint8), np.ones((5, 5), np.uint8))
        p8 = (post * 255).round().astype(np.uint8)
        bg = cv2.inpaint(p8, zone * 255, 4, cv2.INPAINT_TELEA).astype(np.float64) / 255
        base = np.where(zone[..., None] > 0, bg, post)
        base = base * (1 - s_a[..., None])
        out = t_rgb + base * (1 - t_a[..., None])
        # other red elements (the full stops, red details elsewhere) keep their
        # exact original pixels: no shadow from the neighbouring letters on them
        r8 = p8.astype(int)
        other_red = (r8[..., 0] > 120) & (r8[..., 0] - r8[..., 1] > 60) & (r8[..., 0] - r8[..., 2] > 45) & (zone == 0)
        protect = cv2.dilate(other_red.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        touched = ((zone > 0) | (s_a > 1 / 512) | (t_a > 1 / 512)) & ~(protect & (t_a < 1 / 512))
        out = np.where(touched[..., None], out, post)
        o8 = np.clip(out * 255, 0, 255).round().astype(np.uint8)
        cv2.imwrite(str(OUT / f"{name}_website_embroidery.png"), cv2.cvtColor(o8, cv2.COLOR_RGB2BGR))
        # layers at post resolution, for later adjustment
        cv2.imwrite(str(W / f"{name}_layer_thread_post.png"),
                    cv2.cvtColor(np.dstack([np.clip(t_rgb / np.maximum(t_a[..., None], 1e-6), 0, 1), t_a]).__mul__(255).round().astype(np.uint8), cv2.COLOR_RGBA2BGRA))
        cv2.imwrite(str(W / f"{name}_layer_shadow_post.png"), (s_a * 255).round().astype(np.uint8))
        solid = cv2.erode((t_a > 0.99).astype(np.uint8), np.ones((3, 3))) > 0
        changed = np.abs(o8.astype(int) - p8.astype(int)).max(2) > 0
        far = cv2.dilate((t_a > 0.01).astype(np.uint8), np.ones((31, 31))) == 0
        report[name] = dict(word=WORDS[name], render_mean_luminance=round(float(mean), 4),
                            thread_mean_rgb=[round(v, 1) for v in (o8[solid].mean(0)).tolist()],
                            changed_pixels=int(changed.sum()), changed_far_from_word=int((changed & far).sum()))
        posts.append(o8)
    grid = np.concatenate(posts, axis=1)
    cv2.imwrite(str(OUT / "grid_preview_website_embroidery.png"), cv2.cvtColor(grid, cv2.COLOR_RGB2BGR))
    (OUT / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--thread", default=RENDER_THREAD)
    ap.add_argument("--stage", default="all")
    a = ap.parse_args()
    if a.stage in ("masks", "all"):
        stage_masks()
    if a.stage in ("render", "all"):
        stage_render(a.thread)
    if a.stage in ("composite", "all"):
        stage_composite()
