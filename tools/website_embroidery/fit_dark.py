"""Check whether the red words in posts 04-06 are DARK ExtraBold, and find
the exact placement: fit a high-res DARK rendering of each word (scale x/y +
offset) onto the word's existing anti-aliased coverage in the post, then
report how well the glyph shapes agree.

Usage: python3 tools/website_embroidery/fit_dark.py
"""
import json
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "work" / "website_embroidery"


def load_alpha(p):
    a = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    return (a[..., 3] if a.ndim == 3 and a.shape[2] == 4 else a).astype(np.float64) / 255


def warp(src, sx, sy, tx, ty, shape):
    # blur before the (large) downscale so it behaves like area sampling
    sig = 0.5 / min(sx, sy)
    s = cv2.GaussianBlur(src, (0, 0), sig)
    M = np.float32([[sx, 0, tx], [0, sy, ty]])
    return cv2.warpAffine(s, M, (shape[1], shape[0]), flags=cv2.INTER_LINEAR)


def bbox(a, t=0.5):
    ys, xs = np.nonzero(a > t)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def fit(name):
    post = load_alpha(ROOT / "work" / "embroidery" / f"{name}_mask_alpha.png")
    dark = load_alpha(W / "masks" / f"{name}_dark600.png")
    px0, py0, px1, py1 = bbox(post)
    dx0, dy0, dx1, dy1 = bbox(dark)
    sx0 = (px1 - px0) / (dx1 - dx0)
    sy0 = (py1 - py0) / (dy1 - dy0)
    x0 = [sx0, sy0, px0 - dx0 * sx0, py0 - dy0 * sy0]
    # only compare near the word
    roi = np.zeros_like(post, bool)
    roi[max(py0 - 12, 0):py1 + 12, max(px0 - 12, 0):px1 + 12] = True
    err = lambda p: ((warp(dark, *p, post.shape) - post)[roi] ** 2).sum()
    res = minimize(err, x0, method="Nelder-Mead", options=dict(xatol=1e-4, fatol=1e-3, maxiter=3000))
    sx, sy, tx, ty = res.x
    fitted = warp(dark, sx, sy, tx, ty, post.shape)
    a, b = post > 0.5, fitted > 0.5
    iou = (a & b).sum() / (a | b).sum()
    diff = np.abs(fitted - post)[roi]
    edge = cv2.dilate((a ^ cv2.erode(a.astype(np.uint8), np.ones((3, 3))).astype(bool)).astype(np.uint8), np.ones((3, 3))).astype(bool)
    off_edge = ((a ^ b) & ~edge).sum()
    out = dict(name=name, sx=sx, sy=sy, tx=tx, ty=ty, aspect_ratio_sx_over_sy=sx / sy, iou=float(iou),
               mean_abs_alpha_diff=float(diff.mean()), pixels_disagree=int((a ^ b).sum()),
               disagree_away_from_edges=int(off_edge), word_pixels=int(a.sum()))
    vis = np.dstack([post * 255, fitted * 255, np.zeros_like(post)]).astype(np.uint8)  # red=post, green=DARK, yellow=both
    x0_, y0_, x1_, y1_ = max(px0 - 12, 0), max(py0 - 12, 0), px1 + 12, py1 + 12
    cv2.imwrite(str(W / f"{name}_dark_fit_overlay_x4.png"),
                cv2.resize(vis[y0_:y1_, x0_:x1_, ::-1], None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
    return out


if __name__ == "__main__":
    results = [fit(n) for n in ("POST_04", "POST_05", "POST_06")]
    (W / "dark_fit.json").write_text(json.dumps(results, indent=2))
    for r in results:
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
