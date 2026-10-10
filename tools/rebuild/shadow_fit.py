"""Fit the design's own print shadows (original grid) as a two-term model:
  shade = (1 - k1 * blur(shift(P, d1), s1)) * (1 - k2 * blur(shift(P, d2), s2))
P = union of the print quads (frames.json). Fitted on background pixels near
the prints (not text / dashes / other prints), per colour world.
-> work/rebuild/shadow_fit.json (panel px)"""
import json, sys
from pathlib import Path
import cv2, numpy as np
from scipy.optimize import least_squares
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
from text_runs import RUNS
PANEL_X = {"POST_04": 0, "POST_05": 667, "POST_06": 1333}
STYLE = {"POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}
FLAT = {"beige": np.array([253.1, 239.3, 212.1]), "navy": np.array([0.4, 48.0, 72.3])}
K = 4

def prints_mask(frs, H, W):
    m = np.zeros((H * K, W * K), np.uint8)
    for f in frs: cv2.fillPoly(m, [np.int32(np.round(np.array(f["outer"]) * K * 16))], 1, cv2.LINE_AA, shift=4)
    return cv2.resize(m.astype(np.float32), (W, H), interpolation=cv2.INTER_AREA)

def model(P, p):
    k1, dx1, dy1, s1, k2, dx2, dy2, s2 = p
    sh = lambda m, dx, dy: cv2.warpAffine(m, np.float32([[1, 0, dx], [0, 1, dy]]), m.shape[::-1])
    b1 = cv2.GaussianBlur(sh(P, dx1, dy1), (0, 0), max(s1, 0.3))
    b2 = cv2.GaussianBlur(sh(P, dx2, dy2), (0, 0), max(s2, 0.3))
    return (1 - k1 * b1) * (1 - k2 * b2)

if __name__ == "__main__":
    F = json.loads((ROOT / "work/rebuild/frames.json").read_text())
    g = cv2.cvtColor(cv2.imread(str(ROOT / "source/grid_preview_original.webp")), cv2.COLOR_BGR2RGB).astype(np.float32)
    data = {"beige": [], "navy": []}
    for post in PANEL_X:
        img = g[:, PANEL_X[post]:PANEL_X[post] + 667]; H, W = img.shape[:2]
        P = prints_mask(F[post], H, W)
        lum = img @ np.float32([0.299, 0.587, 0.114])
        flat = FLAT[STYLE[post]] @ [0.299, 0.587, 0.114]
        ok = (cv2.dilate((P > 0.001).astype(np.uint8), np.ones((3, 3))) == 0)
        near = cv2.dilate((P > 0.5).astype(np.uint8), np.ones((121, 121))) > 0
        for r in RUNS[post]:
            x0, y0, x1, y1 = r["box"]; ok[y0 - 4:y1 + 4, x0 - 4:x1 + 4] = False
        # not the dashes / other graphics: hue must match the background world
        a = img - FLAT[STYLE[post]]; chroma = np.abs((a[..., 0] - a[..., 2]) - (a[..., 1] - a[..., 2]) * 0)
        ok &= near & (np.abs(lum - flat) < (130 if STYLE[post] == "beige" else 15))   # navy: shadows move lum by < 10
        ok[:, :2] = ok[:, -2:] = False
        data[STYLE[post]].append((P, lum / flat, ok))
    out = {}
    for style, items in data.items():
        def res(p):
            return np.concatenate([(model(P, p) - r)[ok] for P, r, ok in items])
        p0 = [0.35, 4, 6, 10, 0.25, 1, 1.5, 2]
        fit = least_squares(res, p0, bounds=([0, -20, -20, 0.3, 0, -10, -10, 0.3], [0.95, 30, 30, 40, 0.95, 10, 10, 15]))
        rr = res(fit.x)
        out[style] = dict(zip(["k1", "dx1", "dy1", "s1", "k2", "dx2", "dy2", "s2"], [round(float(v), 4) for v in fit.x]))
        out[style]["rms"] = round(float(np.sqrt((rr ** 2).mean())), 4)
        print(style, out[style])
    (ROOT / "work/rebuild/shadow_fit.json").write_text(json.dumps(out, indent=1))
