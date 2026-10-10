"""Patch artwork extraction (step 1 of the patch pipeline).

source/patches/1X.jpg (white product-shot backgrounds) ->
  work/patches/<name>_art.png    RGBA: the patch's own pixels, unchanged, with
                                 the white background made transparent
  work/patches/<name>_ring.png   the merrowed border band (white = border)
  work/patches/<name>.json       border thread colour + feature sizes

The artwork pixels are never recoloured: alpha is the only thing added. Where
a design has no sewn edge (16 is a printed sticker with a die-cut margin, 19 a
borderless fill-stitch piece), the die-cut outline becomes a merrowed border
like the patches in posts 01-03 (light silver-white overlock thread).
"""
import json, sys
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi

SRC = "source/patches"; OUT = "work/patches"
WORK_LONG = 720   # working resolution (long side), ~5x the size shown in a post

# name, file, mode, border(px at WORK_LONG) , border thread
PATCHES = [
    # sewn edge already in the artwork: ring = its own outer band, own colour
    ("porsche", "15.jpg", "flood", 16, None),
    ("bmo",     "16.jpg", "diecut", 26, "#E9E6DF"),
    ("lifeexe", "17.jpg", "flood", 14, None),
    ("whocares","18.jpg", "flood", 30, None),
    ("cat",     "19.jpg", "diecut", 18, "#E9E6DF"),
]

def fill(m):
    return ndi.binary_fill_holes(m)

def largest(m):
    lab, n = ndi.label(m)
    if n == 0: return m
    s = ndi.sum(m, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(s)))

def run(name, fn, mode, border, thread):
    im = Image.open(f"{SRC}/{fn}").convert("RGB")
    a = np.asarray(im).astype(np.float32)
    dist = np.sqrt(((255 - a) ** 2).sum(-1))           # distance from paper white
    if mode == "flood":
        # background = near-white connected to the image edge
        near = dist < 38
        lab, _ = ndi.label(near)
        edge = np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])
        bg = np.isin(lab, edge[edge > 0])
        sil = largest(fill(~bg))
        sil = ndi.binary_opening(sil, iterations=2)
        art = sil
    else:
        # die-cut: the drawn artwork (non-white), its holes filled; the cut
        # line is the artwork grown by an even margin.
        ink = dist > 60
        ink = ndi.binary_closing(ink, iterations=3)
        art = largest(fill(ink))
        sil = None
    # crop + scale to working size (padding leaves room for border and shadow)
    ys, xs = np.nonzero(art)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    s = WORK_LONG / max(y1 - y0, x1 - x0)
    pad = int(round((border + 34) / s))
    y0 -= pad; x0 -= pad; y1 += pad; x1 += pad
    H, W = a.shape[:2]
    canvas = np.full(((y1 - y0), (x1 - x0), 3), 255, np.uint8)
    cy0, cx0 = max(0, y0), max(0, x0)
    canvas[cy0 - y0:cy0 - y0 + min(y1, H) - cy0, cx0 - x0:cx0 - x0 + min(x1, W) - cx0] = \
        np.asarray(im)[cy0:min(y1, H), cx0:min(x1, W)]
    artc = np.zeros(canvas.shape[:2], bool)
    artc[cy0 - y0:cy0 - y0 + min(y1, H) - cy0, cx0 - x0:cx0 - x0 + min(x1, W) - cx0] = art[cy0:min(y1, H), cx0:min(x1, W)]
    w, h = int(round(canvas.shape[1] * s)), int(round(canvas.shape[0] * s))
    rgb = cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA)
    # anti-aliased alpha from the binary mask at source resolution
    soft = cv2.resize(artc.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    artm = soft > 0.5
    if mode == "flood":
        # smooth the cut contour (product photo edge fuzz), same as die-cut below
        artm = cv2.GaussianBlur(artm.astype(np.float32), (0, 0), 1.6) > 0.5
        alpha = cv2.GaussianBlur(artm.astype(np.float32), (0, 0), 0.6)
        dt = ndi.distance_transform_edt(artm)
        ring = (dt > 0) & (dt <= border)
        # the border's own thread colour (median of the band)
        col = np.median(rgb[ring & (dt > 2)], axis=0)
        thread_hex = "#%02X%02X%02X" % tuple(int(c) for c in col)
        art_rgb = rgb
    else:
        dtout = ndi.distance_transform_edt(~artm)
        silm = dtout <= border
        silm = ndi.binary_closing(silm, iterations=6) | silm
        silm = fill(silm)
        # smooth die-cut contour: blur + threshold
        silf = cv2.GaussianBlur(silm.astype(np.float32), (0, 0), border * 0.35)
        silm = silf > 0.5
        alpha = cv2.GaussianBlur(silm.astype(np.float32), (0, 0), 0.6)
        dtin = ndi.distance_transform_edt(silm)
        ring = silm & ~artm
        thread_hex = thread
        tc = np.array([int(thread[i:i + 2], 16) for i in (1, 3, 5)], np.uint8)
        art_rgb = rgb.copy()
        art_rgb[ring] = tc            # the margin (outside the artwork) is the border thread
    rgba = np.dstack([art_rgb, (np.clip(alpha, 0, 1) * 255).astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(f"{OUT}/{name}_art.png")
    # ring as an RGBA coverage mask (the harness reads coverage from alpha)
    ra = cv2.GaussianBlur(ring.astype(np.float32), (0, 0), 0.6) * (np.clip(alpha, 0, 1))
    Image.fromarray(np.dstack([np.full(ring.shape + (3,), 255, np.uint8), (ra * 255).astype(np.uint8)]), "RGBA").save(f"{OUT}/{name}_ring.png")
    json.dump({"name": name, "src": fn, "size": [w, h], "border_px": border, "thread": thread_hex,
               "mode": mode}, open(f"{OUT}/{name}.json", "w"), indent=1)
    print(name, w, h, thread_hex)

if __name__ == "__main__":
    for p in PATCHES:
        run(*p)
