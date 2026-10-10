"""Fit every text run (DARK ExtraBold, set by the browser at 600 px) onto the
original posts (source/grid_preview_original.webp): one uniform scale + offset
per run, least squares on the run's anti-aliased coverage. -> work/rebuild/text/fit.json
"""
import json, sys
from pathlib import Path
import cv2, numpy as np
from scipy.optimize import minimize
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
from text_runs import RUNS, NAVY, CREAM, RED
T = ROOT / "work/rebuild/text"
PANEL_X = {"POST_04": 0, "POST_05": 667, "POST_06": 1333}
COL = {"navy": NAVY, "cream": CREAM, "red": RED}

def coverage(img, box, colour):
    x0, y0, x1, y1 = box
    roi = img[y0:y1, x0:x1].astype(np.float64)
    border = np.concatenate([roi[0], roi[-1], roi[:, 0], roi[:, -1]])
    bg = np.median(border, axis=0)
    if colour == "red":
        r = roi[..., 0] - roi[..., 1:].max(-1)
        rb = bg[0] - bg[1:].max()
        return np.clip((r - rb) / (np.percentile(r, 99.5) - rb), 0, 1)
    tc = np.array(COL[colour], np.float64)
    d = tc - bg
    a = ((roi - bg) @ d) / (d @ d)
    # only pixels on the bg->text colour line (not red, not other graphics)
    perp = np.linalg.norm((roi - bg) - a[..., None] * d, axis=-1)
    a = np.clip(a, 0, 1) * (perp < 40)
    return a

def warp(src, s, tx, ty, shape):
    g = cv2.GaussianBlur(src, (0, 0), 0.5 / s)
    return cv2.warpAffine(g, np.float32([[s, 0, tx], [0, s, ty]]), (shape[1], shape[0]), flags=cv2.INTER_LINEAR)

def fit_run(img, r, fixed_s=None):
    tgt = coverage(img, r["box"], r["colour"])
    m = cv2.imread(str(T / f"{r['id']}_600.png"), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float64) / 255
    ys, xs = np.nonzero(tgt > 0.5); my, mx = np.nonzero(m > 0.5)
    s0 = ((xs.max() - xs.min()) / (mx.max() - mx.min()) + (ys.max() - ys.min()) / (my.max() - my.min())) / 2
    x0 = [s0, xs.min() - mx.min() * s0, ys.min() - my.min() * s0]
    if fixed_s is None:
        err = lambda p: np.abs(warp(m, *p, tgt.shape) - tgt).sum()   # L1: robust to stray dashes
        res = minimize(err, x0, method="Nelder-Mead", options=dict(xatol=1e-4, fatol=1e-3, maxiter=4000))
        s, tx, ty = res.x
    else:   # a full stop: set at its word's size, only its position is fitted
        s = fixed_s
        cy, cx = np.mean(ys), np.mean(xs); qy, qx = np.mean(my), np.mean(mx)
        x0 = [cx - qx * s, cy - qy * s]
        err = lambda p: np.abs(warp(m, s, *p, tgt.shape) - tgt).sum()
        tx, ty = minimize(err, x0, method="Nelder-Mead", options=dict(xatol=1e-4, fatol=1e-4)).x
    fit = warp(m, s, tx, ty, tgt.shape)
    a, b = tgt > 0.5, fit > 0.5
    iou = (a & b).sum() / max((a | b).sum(), 1)
    vis = np.dstack([tgt * 255, fit * 255, np.zeros_like(tgt)]).astype(np.uint8)
    cv2.imwrite(str(T / f"{r['id']}_fit_x4.png"), cv2.resize(vis[..., ::-1], None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST))
    # placement in panel px: mask px -> panel px
    return dict(id=r["id"], s=s, tx=tx + r["box"][0], ty=ty + r["box"][1], iou=round(float(iou), 4))

if __name__ == "__main__":
    grid = cv2.cvtColor(cv2.imread(str(ROOT / "source/grid_preview_original.webp")), cv2.COLOR_BGR2RGB)
    out = {}
    # the three red words: the verified DARK fits of tools/website_embroidery/fit_dark.py
    # (97-99% IoU; their masks had a 40 px pad, these 60 px: shift by 20 mask px)
    dark = {d["name"]: d for d in json.loads((ROOT / "work/website_embroidery/dark_fit.json").read_text())}
    for post, runs in RUNS.items():
        img = grid[:, PANEL_X[post]:PANEL_X[post] + 667]
        for r in runs:
            if r.get("embroidered"):
                d = dark[post]; s = (d["sx"] + d["sy"]) / 2
                f = dict(id=r["id"], s=s, tx=d["tx"] - 20 * d["sx"], ty=d["ty"] - 20 * d["sy"], iou=round(d["iou"], 4), source="dark_fit.json")
            elif r["text"] == ".":
                d = dark[post]; f = fit_run(img, r, fixed_s=(d["sx"] + d["sy"]) / 2)
            else:
                f = fit_run(img, r)
            out[r["id"]] = f; print(post, f)
    (T / "fit.json").write_text(json.dumps(out, indent=1))
