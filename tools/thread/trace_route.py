"""The reference thread's route (source/reference_dots_thread.jpg), traced.
GUIDES: the visible stretches of the reference thread, as coarse strokes read off the
reference (coordinates of the reference at 1.5x, work/trace/pieces_overlay.png) and in the
reference's own order. Each stroke is snapped to the reference's dash marks next to it
(tools/thread/trace_pieces.marks: dashes on background only) and smoothed; where a
stretch passes behind a photo or sticker in the reference it ends there, as it does in
the reference. Coordinates are mapped to the full six-post grid (F: 3240 x 2700 px,
each reference panel = one whole 1080 x 1350 post).
-> work/trace/route.json"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/thread"))
import trace_pieces as T
from trace_reference import to_full

O = 1.5   # the guides are in 1.5x reference px
GUIDES = {   # name: (points, ends at composition edge: (start, end))
    "01_top_to_02":   ([(455, 0), (500, 40), (560, 85), (620, 115), (690, 140)], (True, False)),
    "02_03_loop_F":   ([(1200, 400), (1265, 350), (1300, 342), (1350, 352), (1385, 383), (1388, 410), (1370, 440),
                        (1350, 452), (1338, 440), (1345, 415), (1370, 398), (1405, 383), (1425, 375)], (False, False)),
    "03_F_to_edge":   ([(1800, 350), (1840, 310), (1860, 260), (1850, 210), (1835, 170), (1840, 135), (1870, 95), (1920, 62)], (False, True)),
    "01_big_curve":   ([(0, 180), (45, 212), (75, 250), (70, 300), (48, 350), (38, 400), (48, 450), (75, 488), (105, 510),
                        (160, 530), (220, 540), (280, 536), (340, 523), (415, 512), (455, 520), (500, 548), (550, 570),
                        (615, 558), (660, 540), (700, 515)], (True, False)),
    "02_03_06_low":   ([(1175, 660), (1205, 695), (1240, 722), (1283, 738), (1360, 732), (1440, 736), (1490, 760),
                        (1520, 790), (1535, 815)], (False, False)),
    "06_05_mid":      ([(1372, 960), (1335, 983), (1300, 1012), (1268, 1035), (1235, 1050)], (False, False)),
    "05_top_curve":   ([(780, 878), (840, 862), (900, 855), (960, 858), (982, 885), (990, 922)], (False, False)),
    "05_life_to_04":  ([(765, 990), (742, 1035), (720, 1080), (690, 1125), (660, 1160), (637, 1175), (605, 1190), (585, 1200)], (False, False)),
    "04_top_curve":   ([(245, 798), (200, 815), (150, 842), (115, 872), (103, 905), (115, 938), (150, 956), (205, 964),
                        (255, 968), (300, 985)], (False, False)),
    "04_left_a":      ([(0, 1245), (25, 1222), (55, 1200)], (True, False)),
    "04_left_clock":  ([(0, 1285), (15, 1310), (45, 1335), (68, 1342)], (True, False)),
    "04_clock_right": ([(150, 1395), (200, 1415), (260, 1438), (345, 1445)], (False, False)),
    "04_05_bottom":   ([(590, 1495), (640, 1500), (690, 1500), (740, 1488), (790, 1462)], (False, False)),
    "05_06_bmo":      ([(1230, 1440), (1262, 1470), (1290, 1492), (1330, 1520), (1375, 1530)], (False, False)),
    "06_bmo_right":   ([(1515, 1510), (1540, 1480), (1560, 1430), (1600, 1390), (1660, 1370), (1730, 1350), (1810, 1330),
                        (1860, 1310), (1890, 1280), (1905, 1240), (1900, 1200), (1870, 1150), (1830, 1100)], (False, False)),
}
SNAP = 9.0   # ref px

def snap(guide, marks):
    """the guide, densified, each sample nudged onto the reference's dashes next to it:
    every mark pulls its nearest guide sample along the normal; the pulls are spread
    smoothly along the stroke (the guide's shape stays; the marks set its exact place)"""
    G = np.array(guide, float) / O
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(G, axis=0).T))]
    s = np.arange(0, d[-1] + 1e-6, 1.0)
    D = np.c_[np.interp(s, d, G[:, 0]), np.interp(s, d, G[:, 1])]
    T_ = np.gradient(D, axis=0); T_ /= np.linalg.norm(T_, axis=1, keepdims=True) + 1e-9
    N = np.c_[-T_[:, 1], T_[:, 0]]
    off = np.zeros(len(D)); wgt = np.zeros(len(D)); used = 0
    for m in marks:
        p = np.array([m["x"], m["y"]])
        k = int(np.argmin(np.hypot(*(D - p).T)))
        if np.hypot(*(D[k] - p)) > SNAP: continue
        off[k] += (p - D[k]) @ N[k]; wgt[k] += 1; used += 1
    if used:
        sig = 12.0; r = int(3 * sig); g = np.exp(-0.5 * (np.arange(-r, r + 1) / sig) ** 2)
        num = np.convolve(np.pad(off, r), g, "valid"); den = np.convolve(np.pad(wgt, r), g, "valid")
        o = np.where(den > 0.05, num / np.maximum(den, 1e-9), 0) * np.clip(den / 0.3, 0, 1)
        D = D + N * o[:, None]
    return D, used

def smooth_line(pts, step=0.5, sig=6.0):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]
    s = np.arange(0, d[-1], step)
    P = np.c_[np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])]
    k = int(sig / step * 3); g = np.exp(-0.5 * (np.arange(-k, k + 1) * step / sig) ** 2); g /= g.sum()
    pad = np.vstack([np.repeat(P[:1], k, 0), P, np.repeat(P[-1:], k, 0)])
    return np.c_[np.convolve(pad[:, 0], g, "valid"), np.convolve(pad[:, 1], g, "valid")]

if __name__ == "__main__":
    M = T.marks()
    route = {}
    for name, (g, edges) in GUIDES.items():
        P, S = snap(g, M)
        P = smooth_line(P, sig=2.5)
        F = np.array([to_full(x, y) for x, y in P])
        route[name] = dict(points=F.round(2).tolist(), marks=int(S), edge_start=edges[0], edge_end=edges[1])
        print(f"{name:16s} marks {S:3d}  F {F[0].round(0)} -> {F[-1].round(0)}")
    (ROOT / "work/trace/route.json").write_text(json.dumps(route))
