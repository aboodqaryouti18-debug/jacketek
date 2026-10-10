"""Posts 01-03 with the striped background of posts 04-06, at 1080 x 1350.

The only source for posts 01-03 is the grid (source/embroidery_reference_posts01-03.webp,
one 667 x 888 panel per post), so their content is kept exactly as it is and only the
background underneath it is replaced:

  1. each panel is split against its old plain background (navy: flat; beige: its light
     model, work/rebuild/ref_background.json):
       foreground  everything that is not plain background (photos, patches, type,
                   dashed lines, logos), as a soft matte; solid prints are filled so the
                   navy inside a photo stays photo
       shade       the background pixels' brightness relative to the plain background
                   (the design's own shadows), filled in under the foreground
  2. the striped background of posts 04-06 is rendered at 1080 x 1350 for the post's own
     colour world (tools/rebuild/compose.py: the hairlines, the website world, the site
     grain): 01 navy, 02 beige, 03 navy
  3. result = striped background x shade (upscaled) + foreground (upscaled)

Panel -> post: the grid shows the centre 3:4 of each 4:5 post (as for 04-06), so the
side strips outside the panel are background; dashed guides that leave the panel are
continued into them.

Usage: python3 tools/posts0103/compose0103.py [POST_01 POST_02 POST_03]
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
import compose as C  # noqa: E402

GRID = ROOT / "source/embroidery_reference_posts01-03.webp"
PANEL_X = {"POST_01": 0, "POST_02": 667, "POST_03": 1333}
PANEL_W = {"POST_01": 667, "POST_02": 666, "POST_03": 667}
STYLE = {"POST_01": "navy", "POST_02": "beige", "POST_03": "navy"}
OUT = ROOT / "export/posts01-03_striped_1080x1350"
WK = ROOT / "work/posts0103"
LUM = np.float32([0.299, 0.587, 0.114])
SHARPEN = 0.35

# register 01-03 with the 04-06 compositor (same functions, same settings)
C.PANEL_W.update(PANEL_W); C.STYLE.update(STYLE)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def old_background(post, H, W):
    R = json.loads((ROOT / "work/rebuild/ref_background.json").read_text())
    if STYLE[post] == "navy":
        return np.ones((H, W, 3), np.float32) * np.float32(R["navy"]["colour"])
    q = R["beige"]["params"]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = (xx + 0.5) / W, (yy + 0.5) / H
    f = np.clip((v - q["floor_from"]) / (1 - q["floor_from"]), 0, 1)
    g = (1 - q["a_u"] * ((u - 0.5) / 0.5) ** 2 - q["a_v"] * ((v - q["v_centre"]) / 0.5) ** 2) * (1 - q["floor"] * f * f)
    return (np.float32(R["beige"]["peak_colour"]) * g[..., None]).astype(np.float32)


def split(post):
    g = cv2.cvtColor(cv2.imread(str(GRID)), cv2.COLOR_BGR2RGB).astype(np.float32)
    p = g[:, PANEL_X[post]:PANEL_X[post] + PANEL_W[post]]
    H, W = p.shape[:2]
    bg = old_background(post, H, W)
    # brightness of each pixel relative to the plain background, and how far its
    # colour is from "the background, only lighter or darker"
    gain = np.clip((p @ LUM) / np.maximum(bg @ LUM, 1), 0, 1.2)
    resid = np.abs(p - gain[..., None] * bg).max(2)
    # the old background is near-flat, so a darker pixel of the same hue is a shadow
    a = smoothstep(7, 24, resid)
    # the grid's panel seams (1-2 px of the neighbouring post / a light gap): background
    seam = np.zeros((H, W), bool); seam[:, :2] = seam[:, -3:] = True
    a[seam] = 0; gain[seam] = 1
    # solid prints (photos, patches): fill their holes, so dark navy inside a photo
    # stays part of the photo (letters keep their open counters: low fill ratio)
    solid = a > 0.5
    lab, n = ndi.label(solid)
    filled = solid.copy()
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == i
        area = comp.sum(); box = comp.size
        if area > 2500 and area / box > 0.45:
            filled[sl] |= ndi.binary_fill_holes(comp)
    a = np.maximum(a, cv2.GaussianBlur(filled.astype(np.float32), (0, 0), 0.6) * (filled > 0))
    # shade: the background's own brightness (shadows), filled in under the foreground
    w = (1 - a) ** 4
    num = cv2.GaussianBlur(gain * w, (0, 0), 2.5); den = cv2.GaussianBlur(w, (0, 0), 2.5)
    fill = num / np.maximum(den, 1e-4)
    shade = np.where(den > 0.25, gain * w + fill * (1 - w), fill)
    # where nothing is known for far (inside big prints): 1 (they cover it anyway)
    far = den < 0.02
    shade[far] = 1.0
    shade = cv2.GaussianBlur(shade.astype(np.float32), (0, 0), 0.7)
    return p, a.astype(np.float32), shade.astype(np.float32), bg


def to_canvas(img, post, interp):
    M = C.A(post)[:2].astype(np.float32)
    return cv2.warpAffine(img, M, (C.W_OUT, C.H_OUT), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def subject(a):
    big = cv2.erode((a > 0.5).astype(np.uint8), np.ones((9, 9))) > 0
    ys, xs = np.nonzero(big)
    return float(xs.mean() / a.shape[1]), float(ys.mean() / a.shape[0])


def build(post):
    p, a, shade, bg_old = split(post)
    C.SUBJECT[post] = subject(a)
    grain = cv2.cvtColor(cv2.imread("/home/user/jacketportable/public/assets/texture/grain-soft-240.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32)
    style = STYLE[post]
    # the striped background of posts 04-06 (compose.background without the 04-06 prints)
    bg = np.ones((C.H_OUT, C.W_OUT, 3), np.float32) * C.FLAT[style].astype(np.float32)
    bg *= C.lines_gain(post)[..., None]
    w, mid = C.world(post, grain)
    bg = np.clip(bg + (w - mid), 0, 255)
    # shade (the design's shadows): smooth, bilinear; outside the panel: 1
    sh = to_canvas(shade - 1, post, cv2.INTER_LINEAR) + 1
    out = bg * sh[..., None]
    # foreground: premultiplied, Lanczos
    fa = np.clip(to_canvas(a, post, cv2.INTER_LANCZOS4), 0, 1)
    fc = np.clip(to_canvas(p * a[..., None], post, cv2.INTER_LANCZOS4), 0, 255)
    # clarity: the source is the 667 px grid, so after the 1.52x Lanczos upscale a light
    # unsharp mask (radius ~1 output px, 35%) on the foreground only; no detail is invented
    fc = np.clip(fc + SHARPEN * (fc - cv2.GaussianBlur(fc, (0, 0), 1.1)), 0, 255)
    out = fc + out * (1 - fa[..., None])
    WK.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(WK / f"{post}_matte.png"), (a * 255).astype(np.uint8))
    cv2.imwrite(str(WK / f"{post}_shade.png"), np.clip(shade * 200, 0, 255).astype(np.uint8))
    return np.clip(out, 0, 255)


if __name__ == "__main__":
    posts = sys.argv[1:] or ["POST_01", "POST_02", "POST_03"]
    (WK / "stage").mkdir(parents=True, exist_ok=True)
    for post in posts:
        img = build(post)
        cv2.imwrite(str(WK / "stage" / f"{post}.png"), cv2.cvtColor(img.round().astype(np.uint8), cv2.COLOR_RGB2BGR))
        print(post, "ok", C.SUBJECT[post])
