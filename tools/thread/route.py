"""Plan ONE continuous thread across the six-post composition (G coordinates, see layout.py:
the profile grid, top row 01 02 03, bottom row 04 05 06, 1014 x 1350 px per visible panel).

The route is planned on the whole grid at once (work/thread/occupancy_grid.png):
  01  enters from the left, loops in the open navy pocket under the headline, runs down
      between the stickers and the copy, crosses into 04
  04  sweeps through the open band above the headline, crosses into 05
  05  a loop in the open band beside the LIFE.EXE patch, rises back into 02
  02  climbs the left margin and passes behind the polaroids (a thread under the prints),
      out through the right margin into 03
  03  down the open left side, a loop under the F patch, between the among-us sticker and
      the copy, along the bottom band, crosses into 06
  06  out through the open band right of the cat, leaving on the right
Through these control points: a centripetal Catmull-Rom spline, then the loops (trochoid
turns) inserted at their points. -> work/thread/path.json (dense polyline, G px)"""
import json, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/thread"))
import layout as L
W = ROOT / "work/thread"

CTRL = [(-90, 520), (40, 560), (190, 620), (330, 660),          # 01: enters from the left
        (520, 760), (590, 880), (520, 1010), (470, 1130), (530, 1265),
        (600, 1350),                                            # 01 | 04
        (680, 1415), (850, 1445), (1014, 1440),                 # 04 band -> 04 | 05
        (1130, 1460), (1225, 1415),                             # 05: one broad turn up
        (1240, 1350),                                           # 05 | 02
        (1180, 1280), (1065, 1190), (1038, 1000), (1042, 800),  # 02 left margin
        (1300, 640), (1700, 520), (1985, 440),                  # behind the polaroids
        (2026, 425),                                            # 02 | 03
        (2075, 450), (2112, 560), (2105, 690), (2110, 790),     # 03 left side (loop at 790)
        (2125, 900), (2170, 1040), (2230, 1170),                # behind the among-us sticker
        (2400, 1255), (2700, 1285), (2905, 1315),               # 03 bottom band
        (2960, 1350),                                           # 03 | 06
        (2995, 1420), (3008, 1540), (3030, 1640), (3120, 1720)] # 06: down the right margin, out
# two loops (reference: few, round): (control index, radius G px, side +1 / -1)
LOOPS = [(3, 46, 1), (27, 40, 1)]

def catmull(P, n=40, alpha=0.5):
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0; t1 = t0 + np.linalg.norm(p1 - p0) ** alpha; t2 = t1 + np.linalg.norm(p2 - p1) ** alpha; t3 = t2 + np.linalg.norm(p3 - p2) ** alpha
        t = np.linspace(t1, t2, n, endpoint=False)[:, None]
        A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
        B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
        out.append((t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2)
    out.append(P[-2][None])
    return np.vstack(out)

def resample(P, step):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = np.arange(0, d[-1], step)
    return np.c_[np.interp(s, d, P[:, 0]), np.interp(s, d, P[:, 1])], s

if __name__ == "__main__":
    C = np.array(CTRL, float)
    P, s = resample(catmull(C), 1.0)
    # where each control point lies on the path
    ci = [int(np.argmin(np.hypot(*(P - c).T))) for c in C]
    pieces, last = [], 0
    for k, r, turn in LOOPS:
        i = ci[k]
        span = int(r * 0.9)                                # chord 1.8 r: a round loop
        a, b = i - span, i + span
        pieces.append(P[last:a])
        t = P[b] - P[a]; Lr = np.linalg.norm(t); t /= Lr; n = np.array([-t[1], t[0]]) * turn
        u = np.linspace(0, 1, 400)[:, None]
        # a trochoid: progress along the chord + one full turn of radius r
        # (a prolate trochoid: forward at both ends, turning back only at its top)
        pieces.append(P[a] + u * Lr * t + r * (np.sin(2 * np.pi * u) * t + (1 - np.cos(2 * np.pi * u)) * n))
        last = b
    pieces.append(P[last:])
    Q = np.vstack(pieces)
    # soften the joins of the loops (a short running mean)
    k = 15; ker = np.ones(k) / k
    Qs = np.c_[np.convolve(np.pad(Q[:, 0], k, mode="edge"), ker, "same")[k:-k], np.convolve(np.pad(Q[:, 1], k, mode="edge"), ker, "same")[k:-k]]
    Q, _ = resample(Qs, 1.0)
    (W / "path.json").write_text(json.dumps(dict(points=np.round(Q, 2).tolist(), control=CTRL, loops=LOOPS)))
    print("path length", len(Q), "G px")
