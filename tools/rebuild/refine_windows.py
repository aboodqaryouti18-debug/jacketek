"""Refine each photo/card window edge (frames.json) to the strongest white->content
luminance step along the edge normal (sub-pixel, robust line fit). Also sets the
sleeve-number frame's hidden top edge (under the JK frame) parallel to its bottom."""
import json
from pathlib import Path
import cv2, numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter1d
ROOT = Path(__file__).resolve().parents[2]
PANEL_X = {"POST_04": 0, "POST_05": 667, "POST_06": 1333}

def line_from(p, q):
    return np.array(p, float), np.array(q, float)

def refine_edge(L, p, q, inward):
    d = (q - p) / np.linalg.norm(q - p); n = inward
    ts = np.linspace(0.1, 0.9, 60)
    offs = np.arange(-4, 4.01, 0.1)
    pts = []
    for t in ts:
        base = p + (q - p) * t
        xy = base[None] + offs[:, None] * n[None]
        prof = map_coordinates(L, [xy[:, 1], xy[:, 0]], order=1)
        dp = np.gradient(gaussian_filter1d(prof, 4))
        i = np.argmin(dp)                                    # white -> darker content, going inward
        if dp[i] < -0.6: pts.append(base + offs[i] * n)
    pts = np.array(pts)
    if len(pts) < 12: return p, q, len(pts)
    # robust line: offset along n as a function of t
    s = (pts - p) @ n; t = (pts - p) @ d
    for _ in range(3):
        k, b = np.polyfit(t, s, 1); r = np.abs(s - (k * t + b)); keep = r < max(0.25, 2 * np.median(r))
        s, t = s[keep], t[keep]
    k, b = np.polyfit(t, s, 1)
    L0 = np.linalg.norm(q - p)
    return p + n * b, q + n * (b + k * L0), len(s)

def intersect(a1, a2, b1, b2):
    da, db = a2 - a1, b2 - b1
    A = np.array([da, -db]).T
    t = np.linalg.solve(A, b1 - a1)
    return a1 + da * t[0]

if __name__ == "__main__":
    F = json.loads((ROOT / "work/rebuild/frames.json").read_text())
    g = cv2.cvtColor(cv2.imread(str(ROOT / "source/grid_preview_original.webp")), cv2.COLOR_BGR2RGB).astype(np.float64)
    lum = g @ [0.299, 0.587, 0.114]
    for post, frs in F.items():
        L = lum[:, PANEL_X[post]:PANEL_X[post] + 667]
        for f in frs:
            w = np.array(f["window"], float); c = w.mean(0)
            lines, sup = [], []
            for i in range(4):
                p, q = w[i], w[(i + 1) % 4]
                d = (q - p) / np.linalg.norm(q - p); n = np.array([-d[1], d[0]])
                if (c - p) @ n < 0: n = -n
                p2, q2, k = refine_edge(L, p, q, n); lines.append((p2, q2)); sup.append(k)
            nw = [intersect(*lines[(i - 1) % 4], *lines[i]) for i in range(4)]   # corner i = edge(i-1) ∩ edge(i)
            f["window_coarse"] = f["window"]; f["window"] = np.round(nw, 3).tolist(); f["window_support"] = sup
            print(post, f["id"], sup, np.abs(np.array(nw) - w).max().round(2))
    # sleeve-number frame: its top edge is hidden under the JK chest frame
    nb = [f for f in F["POST_06"] if f["id"] == "number"][0]
    ch = [f for f in F["POST_06"] if f["id"] == "chest"][0]
    o = np.array(nb["outer"], float)
    bl, br = o[3], o[2]; d = br - bl
    cb_l, cb_r = np.array(ch["outer"][3]), np.array(ch["outer"][2])          # chest frame bottom edge
    x = 150.0; ychest = cb_l[1] + (x - cb_l[0]) / (cb_r[0] - cb_l[0]) * (cb_r[1] - cb_l[1])
    p = np.array([x, ychest - 12]); q = p + d
    tl = intersect(o[0], o[3], p, q); tr = intersect(o[1], o[2], p, q)
    nb["outer"][0], nb["outer"][1] = np.round(tl, 3).tolist(), np.round(tr, 3).tolist()
    nb["note"] = "top edge hidden under the chest frame: set parallel to the bottom edge, 12 px above the chest frame's bottom"
    (ROOT / "work/rebuild/frames.json").write_text(json.dumps(F, indent=1))
