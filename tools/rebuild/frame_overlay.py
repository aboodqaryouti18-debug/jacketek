import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PANEL_X = {"POST_04": 0, "POST_05": 667, "POST_06": 1333}
def quad(c, deg, r):
    t = np.deg2rad(deg); l, tp, rr, b = r
    pts = np.array([[l, tp], [rr, tp], [rr, b], [l, b]])
    R = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    return pts @ R.T + c
if __name__ == "__main__":
    F = json.loads((ROOT / "work/rebuild/frames.json").read_text())
    g = cv2.imread(str(ROOT / "source/grid_preview_original.webp"))
    K = 3
    big = cv2.resize(g, None, fx=K, fy=K, interpolation=cv2.INTER_CUBIC)
    for post, frs in F.items():
        for f in frs:
            for key, col in (("outer", (0, 0, 255)), ("window", (0, 200, 0))):
                q = np.array(f[key]) + [PANEL_X[post], 0]
                cv2.polylines(big, [np.int32(q * K * 4)], True, col, 1, cv2.LINE_AA, shift=2)
    cv2.imwrite("/tmp/claude-0/-home-user/0c8a008e-acb8-50fa-b850-2737be83dd04/scratchpad/frames_x3.png", big)
