"""Find the dashed guide lines of posts 04-06 on the original grid: dash
components (small, elongated, in the post's line colour), grouped into
straight lines (RANSAC); per line: direction, dash length, period, thickness,
phase. -> work/rebuild/dashes.json (panel px)"""
import json, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
from text_runs import RUNS
PANEL_X = {"POST_04": 0, "POST_05": 667, "POST_06": 1333}
STYLE = {"POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}

def dash_components(img, style, post):
    a = img.astype(np.float64)
    if style == "beige":
        bg = np.array([253, 239, 212.]); tc = np.array([0, 48, 72.])
    else:
        bg = np.array([0, 48, 72.]); tc = np.array([253, 240, 214.])
    d = tc - bg; cov = np.clip(((a - bg) @ d) / (d @ d), 0, 1)
    perp = np.linalg.norm((a - bg) - cov[..., None] * d, axis=-1)
    cov = cov * (perp < 45)
    m = (cov > 0.35).astype(np.uint8)
    for r in RUNS[post]:                      # not inside text
        x0, y0, x1, y1 = r["box"]; m[y0:y1, x0:x1] = 0
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    comps = []
    for i in range(1, n):
        if not (4 <= st[i, 4] <= 60): continue
        ys, xs = np.nonzero(lab == i)
        w = cov[ys, xs]
        pts = np.c_[xs, ys].astype(float)
        mu = (pts * w[:, None]).sum(0) / w.sum()
        C = np.cov((pts - mu).T, aweights=w)
        ev, evec = np.linalg.eigh(C)
        if ev[1] < 2.5 * max(ev[0], 0.05): continue          # elongated only
        comps.append(dict(c=mu, dir=evec[:, 1], area=float(w.sum())))
    return comps, cov

def ransac_lines(comps):
    P = np.array([c["c"] for c in comps]); D = np.array([c["dir"] for c in comps])
    left = list(range(len(P))); lines = []
    rng = np.random.default_rng(0)
    while len(left) >= 3:
        best = None
        for _ in range(400):
            i = rng.choice(left)
            d = D[i]; nrm = np.array([-d[1], d[0]])
            dist = np.abs((P[left] - P[i]) @ nrm)
            ang = np.abs(D[left] @ d)
            inl = [left[k] for k in np.nonzero((dist < 1.2) & (ang > 0.97))[0]]
            if best is None or len(inl) > len(best): best = inl
        if len(best) < 3: break
        lines.append(best); left = [k for k in left if k not in best]
    return lines

if __name__ == "__main__":
    g = cv2.cvtColor(cv2.imread(str(ROOT / "source/grid_preview_original.webp")), cv2.COLOR_BGR2RGB)
    out = {}
    for post in PANEL_X:
        img = g[:, PANEL_X[post]:PANEL_X[post] + 667]
        comps, cov = dash_components(img, STYLE[post], post)
        res = []
        for L in ransac_lines(comps):
            P = np.array([comps[k]["c"] for k in L])
            mu = P.mean(0); _, _, vt = np.linalg.svd(P - mu); d = vt[0]
            if d[0] < 0: d = -d
            t = np.sort((P - mu) @ d)
            gaps = np.diff(t); period = np.median(gaps[gaps < np.median(gaps) * 1.5])
            # dash length / thickness from the coverage along / across the line
            area = np.median([comps[k]["area"] for k in L])
            phase = np.median((t - t[0]) % period)
            res.append(dict(p0=(mu + d * t[0]).round(3).tolist(), p1=(mu + d * t[-1]).round(3).tolist(),
                            dir=d.round(5).tolist(), period=round(float(period), 3), n=len(L),
                            dash_area=round(float(area), 2)))
            print(post, res[-1])
        out[post] = res
    (ROOT / "work/rebuild/dashes.json").write_text(json.dumps(out, indent=1))
