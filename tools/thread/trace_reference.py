"""Trace the reference thread (source/reference_dots_thread.jpg): the dash marks, in
full-post coordinates (each reference panel = one whole 1080x1350 post).
Reference panels: columns x 0|425|855|1280, rows y 0|531|1065.
-> work/trace/dashes.json  (dash centres + directions, in F = full-grid px, 3240 x 2700)"""
import json
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "source/reference_dots_thread.jpg"
XB, YB = [0, 425, 855, 1280], [0, 531, 1065]
STYLE = [["navy", "beige", "navy"], ["beige", "navy", "beige"]]

def to_full(x, y):
    c = 0 if x < XB[1] else (1 if x < XB[2] else 2); r = 0 if y < YB[1] else 1
    return (c * 1080 + (x - XB[c]) / (XB[c + 1] - XB[c]) * 1080, r * 1350 + (y - YB[r]) / (YB[r + 1] - YB[r]) * 1350)

if __name__ == "__main__":
    a = cv2.imread(str(REF)).astype(np.float32)[..., ::-1]
    L = a @ [0.299, 0.587, 0.114]
    out = []
    for r in range(2):
        for c in range(3):
            x0, x1, y0, y1 = XB[c] + 2, XB[c + 1] - 2, YB[r] + 2, YB[r + 1] - 2
            p = L[y0:y1, x0:x1]; bg = cv2.medianBlur(p.astype(np.uint8), 15).astype(np.float32)
            d = (p - bg) if STYLE[r][c] == "navy" else (bg - p)        # cream on navy / navy on beige
            m = (d > 45).astype(np.uint8)
            n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
            for i in range(1, n):
                area = st[i, 4]
                if not (6 <= area <= 60): continue
                ys, xs = np.nonzero(lab == i)
                pts = np.c_[xs, ys].astype(float)
                C = np.cov(pts.T) if len(pts) > 2 else np.eye(2)
                ev, evec = np.linalg.eigh(C)
                length = 4 * np.sqrt(max(ev[1], 1e-6)); width = 4 * np.sqrt(max(ev[0], 1e-6))
                if length < 5 or length / max(width, 0.5) < 2.2: continue          # dashes, not dots
                cx, cy = pts.mean(0)
                fx, fy = to_full(cx + x0, cy + y0)
                out.append(dict(panel=[r, c], x=round(fx, 1), y=round(fy, 1), dir=evec[:, 1].round(4).tolist(),
                                length=round(length * 2.535, 1), width=round(width * 2.535, 2)))
    (ROOT / "work/trace/dashes.json").write_text(json.dumps(out, indent=1))
    print(len(out), "dash marks")
    # overlay for checking
    vis = cv2.imread(str(REF))
    for d in out:
        r, c = d["panel"]
        X = XB[c] + (d["x"] - c * 1080) / 1080 * (XB[c + 1] - XB[c]); Y = YB[r] + (d["y"] - r * 1350) / 1350 * (YB[r + 1] - YB[r])
        cv2.circle(vis, (int(X), int(Y)), 3, (0, 0, 255), -1)
    cv2.imwrite(str(ROOT / "work/trace/dashes_overlay.png"), vis)
