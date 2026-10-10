"""Dashed guide lines as vectors (panel px), from the dash centres measured on the
original grid (measure_dashes.py). Each line: a circular arc (or straight line)
through its dashes, dash period + phase fitted along the arc, dash 9.1 x 1.8 px
(measured), drawn UNDER the prints and the type (as in the design). Lines that
leave the visible 3:4 panel are continued to the 4:5 post edge.
-> work/rebuild/dash_model.json"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares
ROOT = Path(__file__).resolve().parents[2]
DASH_LEN, DASH_W = 9.1, 1.8
# (the dash at 212.8,161.8 is partly covered by the type's dots: left out of the fit, still drawn)
LINES = {
    "POST_04": [
        dict(id="arc_top_left", pts=[[3.0, 2.5], [16.3, 14.0], [30.1, 25.4], [43.7, 36.9], [57.4, 48.0], [71.2, 59.2], [85.0, 70.1],
             [99.3, 81.3], [113.4, 92.0], [127.3, 102.6], [141.7, 113.1], [156.2, 123.6], [170.5, 133.5], [185.2, 143.6],
             [200.2, 153.5], [230.0, 172.5], [245.0, 181.8], [260.3, 191.0], [275.7, 200.1], [290.9, 209.0], [306.2, 217.8]],
             extend_start=True, extend_end=False),
        # one dash cut by the 04 | 05 boundary: the line continues in the next post (05 left)
        dict(id="to_05", pts=[[662.8, 368.3], [667 + 1.7, 369.4], [667 + 16.4, 374.2]], straight=True, angle=19.5,
             anchor=[667 + 16.4, 374.2], extend_start=False, extend_end=True, from_x=650),
    ],
    "POST_05": [
        dict(id="from_04", pts=[[1.7 - 667 + 667, 369.4]], straight=True, angle=19.5, anchor=[16.4, 374.2],
             extend_start=True, extend_end=False, to_x=30),
        dict(id="to_06", straight=True, angle=16.6, anchor=[666 + 5.3, 547.4], extend_start=False, extend_end=True, from_x=652),
    ],
    "POST_06": [
        dict(id="from_05", straight=True, angle=16.6, anchor=[5.3, 547.4], extend_start=True, extend_end=False, to_x=12),
        dict(id="arc_text", pts=[[340.8, 662.9], [356.9, 670.0], [484.1, 733.3], [498.7, 743.3], [513.2, 753.8],
                                  [633.9, 858.3], [647.1, 870.2], [659.9, 881.8]], extend_start=False, extend_end=True),
    ],
}

def fit_circle(P):
    x, y = P.T
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    c = np.linalg.lstsq(A, x ** 2 + y ** 2, rcond=None)[0]
    cx, cy = c[0], c[1]; r = np.sqrt(c[2] + cx ** 2 + cy ** 2)
    res = least_squares(lambda p: np.hypot(x - p[0], y - p[1]) - p[2], [cx, cy, r])
    return res.x

def arc_model(P):
    cx, cy, r = fit_circle(P)
    th = np.unwrap(np.arctan2(P[:, 1] - cy, P[:, 0] - cx))
    sign = float(np.sign(th[-1] - th[0]))
    s = (th - th[0]) * r * sign                           # arclength from the first dash (increasing)
    # period + phase: s_i = s0 + k_i * period (k_i integers from a first guess)
    gaps = np.diff(s); p0 = np.median(gaps[gaps < 1.4 * np.median(gaps)])
    k = np.round((s - s[0]) / p0)
    A = np.c_[np.ones(len(k)), k]; s0, per = np.linalg.lstsq(A, s, rcond=None)[0]
    resid = s - (s0 + k * per)
    ks = sorted(set(int(v) for v in k))
    # stretches the original does not show (the line is knocked out behind the type)
    hidden = [[a + 1, b - 1] for a, b in zip(ks, ks[1:]) if b - a > 2]   # 2+ missing dashes in a row
    return dict(kind="arc", cx=cx, cy=cy, r=r, th0=th[0], sign=sign, s0=s0, period=per,
                s_first=s0, s_last=s0 + k.max() * per, resid_max=float(np.abs(resid).max()), hidden_k=hidden)

if __name__ == "__main__":
    out = {}
    per04 = None
    for post, lines in LINES.items():
        out[post] = []
        for L in lines:
            if L.get("straight"):
                out[post].append(dict(id=L["id"], kind="line", anchor=L["anchor"], angle=L["angle"],
                                      extend_start=L["extend_start"], extend_end=L["extend_end"],
                                      from_x=L.get("from_x"), to_x=L.get("to_x")))
            else:
                m = arc_model(np.array(L["pts"], float))
                m.update(id=L["id"], extend_start=L["extend_start"], extend_end=L["extend_end"])
                out[post].append({k: (float(v) if isinstance(v, (np.floating, float)) else v) for k, v in m.items()})
                print(post, L["id"], "r", round(m["r"], 1), "period", round(m["period"], 3), "resid max", round(m["resid_max"], 2))
    periods = [l["period"] for p in out.values() for l in p if l["kind"] == "arc"]
    for p in out.values():
        for l in p:
            if l["kind"] == "line": l["period"] = float(np.mean(periods))
    out["dash"] = dict(length=DASH_LEN, width=DASH_W)
    (ROOT / "work/rebuild/dash_model.json").write_text(json.dumps(out, indent=1))
