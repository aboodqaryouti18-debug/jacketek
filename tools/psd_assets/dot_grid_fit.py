"""Fit the supplied background's dot lattice per post (1080 px): dots = small, isolated, round
bright (navy) / dark (beige) blobs on clean background; lattice step + phase per axis by
maximising phase coherence; then least-squares refinement on matched dots.
-> work/psd_assets/dot_grid.json"""
import json, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/newbg"))
import replace_background as RB
out = {}
for post in RB.POS:
    pl = RB.plate_raw(post); bg, clean = RB.plate_bg_mask(post, pl)
    L = pl @ RB.LUM; base = cv2.medianBlur(pl.astype(np.uint8), 15).astype(np.float32) @ RB.LUM
    d = (L - base) if RB.STYLE[post] == "navy" else (base - L)
    m = (d > 14).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    ok = (st[:, 4] >= 4) & (st[:, 4] <= 40) & (st[:, 2] <= 8) & (st[:, 3] <= 8)
    ok[0] = False
    C = cen[ok]; C = C[[clean[int(y), int(x)] for x, y in C]] if len(C) else C
    best = {}
    for ax, rng in ((0, np.arange(72, 84, 0.05)), (1, np.arange(70, 82, 0.05))):
        r = [(abs(np.exp(2j * np.pi * C[:, ax] / s).mean()), s) for s in rng]
        coh, s = max(r); z = np.exp(2j * np.pi * C[:, ax] / s).mean()
        best[ax] = (s, (np.angle(z) / (2 * np.pi) * s) % s, coh)
    # refine: assign lattice indices, least squares
    for ax in (0, 1):
        s, ph, _ = best[ax]
        k = np.round((C[:, ax] - ph) / s); res = C[:, ax] - (ph + k * s)
        keep = np.abs(res) < 3
        A = np.c_[np.ones(keep.sum()), k[keep]]; ph2, s2 = np.linalg.lstsq(A, C[keep, ax], rcond=None)[0]
        best[ax] = (float(s2), float(ph2 % s2), float(best[ax][2]), int(keep.sum()), float(np.abs(res[keep]).mean()))
    # dot size / colour from the matched dots
    out[post] = dict(sx=best[0][0], x0=best[0][1], sy=best[1][0], y0=best[1][1], coherence=[best[0][2], best[1][2]],
                     matched=[best[0][3], best[1][3]], mean_residual_px=[best[0][4], best[1][4]], n_dots=int(len(C)))
    print(post, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in out[post].items()})
(ROOT / "work/psd_assets/dot_grid.json").write_text(json.dumps(out, indent=1))
