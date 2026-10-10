"""Measure every white print frame (a quadrilateral: the prints carry a slight skew) of posts 04-06 on the original grid
(source/grid_preview_original.webp): its angle, outer rectangle and photo window,
as sub-pixel edge crossings over many scanlines (medians: the parts another
frame or card hides are outliers). Frame-local axes: u along the width, v down.
-> work/rebuild/frames.json (panel px)
"""
import json
from pathlib import Path
import cv2, numpy as np
from scipy.ndimage import map_coordinates
ROOT = Path(__file__).resolve().parents[2]
PANEL_X = {"POST_04": 0, "POST_05": 667, "POST_06": 1333}
# rough centre, size (w, h) and angle (deg, + = clockwise on screen) per frame
FRAMES = {
    "POST_04": [dict(id="big", c=(333, 413), wh=(597, 382), deg=3.0, kind="photo"),
                dict(id="small", c=(514, 679), wh=(233, 195), deg=-4.8, kind="photo")],
    "POST_05": [dict(id="front", c=(199.1, 543.2), wh=(316.8, 393.7), deg=3.0, kind="photo"),
                dict(id="card1", c=(493.5, 420.3), wh=(265.6, 233.2), deg=-6.0, kind="card"),
                dict(id="card2", c=(492.2, 680.3), wh=(272.2, 227.4), deg=5.0, kind="card")],
    "POST_06": [dict(id="chest", c=(341, 217), wh=(538, 262), deg=3.0, kind="photo"),
                dict(id="number", c=(156, 500), wh=(244, 372), deg=5.8, kind="photo"),
                dict(id="collar", c=(452.1, 472.7), wh=(278.7, 150.6), deg=-5.0, kind="photo")],
}

SLOT_MASK = {("POST_04", "big"): "POST_04_big_mask.png", ("POST_04", "small"): "POST_04_small_mask.png",
             ("POST_05", "front"): "POST_05_front_mask.png", ("POST_06", "number"): "POST_06_number_mask.png",
             ("POST_06", "collar"): "POST_06_collar_mask.png", ("POST_06", "chest"): "POST_06_chest_mask.png"}

def whiteness(img):
    m = img.min(2).astype(np.float64)
    return np.clip((m - 228) / 18, 0, 1)

def sample(f, c, deg, us, vs):
    t = np.deg2rad(deg); cu, su = np.cos(t), np.sin(t)
    U, V = np.meshgrid(us, vs)
    x = c[0] + U * cu - V * su; y = c[1] + U * su + V * cu
    return map_coordinates(f, [y, x], order=1, mode="nearest")

def crossing(prof, axis, inward):
    """sub-pixel positions where prof crosses 0.5, first one met going `inward` from the outside."""
    out = []
    for p in prof:
        idx = np.nonzero(np.diff((p > 0.5).astype(int)) != 0)[0]
        if not len(idx): out.append(np.nan); continue
        i = idx[0] if inward else idx[-1]
        a, b = p[i], p[i + 1]
        out.append(axis[i] + (0.5 - a) / (b - a) * (axis[1] - axis[0]))
    return np.array(out)

def edges(f, fr, c, deg, fw=None):
    fw = f if fw is None else fw
    w, h = fr["wh"]; st = 0.125
    res = {}
    # left / right edges: scan along u over the middle rows
    vs = np.linspace(-h * 0.35, h * 0.35, 120)
    us = np.arange(-w / 2 - 20, -w / 2 + 45, st)          # left: from outside to inside
    P = sample(f, c, deg, us, vs); Pw = sample(fw, c, deg, us, vs)
    res["outer_l"] = crossing(P, us, True)
    res["win_l"] = np.array([crossing(p[None, us > o + 1.5], us[us > o + 1.5], True)[0] if np.isfinite(o) else np.nan for p, o in zip(Pw, res["outer_l"])])
    us = np.arange(w / 2 + 20, w / 2 - 45, -st)
    P = sample(f, c, deg, us, vs); Pw = sample(fw, c, deg, us, vs)
    res["outer_r"] = crossing(P, us, True)
    res["win_r"] = np.array([crossing(p[None, us < o - 1.5], us[us < o - 1.5], True)[0] if np.isfinite(o) else np.nan for p, o in zip(Pw, res["outer_r"])])
    res["v_lr"] = vs
    us = np.linspace(-w * 0.35, w * 0.35, 160)
    vs_t = np.arange(-h / 2 - 20, -h / 2 + 45, st)
    P = sample(f, c, deg, us, vs_t).T; Pw = sample(fw, c, deg, us, vs_t).T
    res["outer_t"] = crossing(P, vs_t, True)
    res["win_t"] = np.array([crossing(p[None, vs_t > o + 1.5], vs_t[vs_t > o + 1.5], True)[0] if np.isfinite(o) else np.nan for p, o in zip(Pw, res["outer_t"])])
    vs_b = np.arange(h / 2 + 20, h / 2 - 70, -st)
    P = sample(f, c, deg, us, vs_b).T; Pw = sample(fw, c, deg, us, vs_b).T
    res["outer_b"] = crossing(P, vs_b, True)
    res["win_b"] = np.array([crossing(p[None, vs_b < o - 1.5], vs_b[vs_b < o - 1.5], True)[0] if np.isfinite(o) else np.nan for p, o in zip(Pw, res["outer_b"])])
    res["u_tb"] = us
    return res

def robust_line(x, y):
    ok = np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(y) < 10: return np.nan, np.nan, 0
    for _ in range(3):
        k, b = np.polyfit(x, y, 1)
        r = np.abs(y - (k * x + b)); keep = r < max(0.35, np.percentile(r, 60) * 2)
        x, y = x[keep], y[keep]
    k, b = np.polyfit(x, y, 1)
    return k, b, len(y)

def corners(L, pre):
    """intersection of the four fitted edge lines (local coords): l/r: u = k v + b, t/b: v = k u + b"""
    def lr(k): return L[pre + "_" + k][:2]
    out = []
    for a, bb in (("l", "t"), ("r", "t"), ("r", "b"), ("l", "b")):
        k1, b1 = lr(a); k2, b2 = lr(bb)
        v = (k2 * b1 + b2) / (1 - k1 * k2); u = k1 * v + b1
        out.append((u, v))
    return np.array(out)

def to_panel(q, c, deg):
    t = np.deg2rad(deg)
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    return q @ R.T + c

def measure(img, fr, slot=None):
    f = whiteness(img)
    c, deg = np.array(fr["c"], float), fr["deg"]
    e = edges(f, fr, c, deg)
    L = {k: robust_line(e["v_lr"] if k[-1] in "lr" else e["u_tb"], e[k]) for k in e if k[0] in "ow"}
    if slot is not None:
        # photo window: from the visible-photo mask of tools/replace_photos (photo = 0)
        g = 1 - cv2.GaussianBlur(slot, (0, 0), 0.5)
        e2 = edges(f, fr, c, deg, fw=g)
        L.update({k: robust_line(e2["v_lr"] if k[-1] in "lr" else e2["u_tb"], e2[k]) for k in e2 if k[0] == "w"})
    oq = to_panel(corners(L, "outer"), c, deg)
    wq = to_panel(corners(L, "win"), c, deg)
    return dict(id=fr["id"], kind=fr["kind"], outer=oq.round(3).tolist(), window=wq.round(3).tolist(),
                support=[int(L[k][2]) for k in ("outer_l", "outer_t", "outer_r", "outer_b", "win_l", "win_t", "win_r", "win_b")])

if __name__ == "__main__":
    g = cv2.cvtColor(cv2.imread(str(ROOT / "source/grid_preview_original.webp")), cv2.COLOR_BGR2RGB)
    res = {}
    for post, frs in FRAMES.items():
        img = g[:, PANEL_X[post]:PANEL_X[post] + 667]
        res[post] = []
        for fr in frs:
            m = SLOT_MASK.get((post, fr["id"]))
            slot = cv2.imread(str(ROOT / "work/replace_photos" / m), 0).astype(np.float64) / 255 if m else None
            res[post].append(measure(img, fr, slot))
        for r in res[post]: print(post, r)
    (ROOT / "work/rebuild/frames.json").write_text(json.dumps(res, indent=1))
