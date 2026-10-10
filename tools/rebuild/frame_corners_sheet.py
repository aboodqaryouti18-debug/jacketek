import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
PANEL_X = {"POST_04": 0, "POST_05": 667, "POST_06": 1333}
F = json.loads((ROOT / "work/rebuild/frames.json").read_text())
g = cv2.imread(str(ROOT / "source/grid_preview_original.webp"))
import sys
KEY = sys.argv[1] if len(sys.argv) > 1 else "outer"
K = 6; R = 14
big = cv2.resize(g, None, fx=K, fy=K, interpolation=cv2.INTER_CUBIC)
for post, frs in F.items():
    for f in frs:
        for key, col in (("outer", (0, 0, 255)), ("window", (0, 190, 0))):
            q = np.array(f[key]) + [PANEL_X[post], 0]
            if np.isfinite(q).all(): cv2.polylines(big, [np.int32(q * K * 4)], True, col, 1, cv2.LINE_AA, shift=2)
tiles = []
for post, frs in F.items():
    for f in frs:
        row = []
        for (x, y) in f[KEY]:
            x += PANEL_X[post]
            x0, y0 = int((x - R) * K), int((y - R) * K)
            t = big[max(0, y0):y0 + 2 * R * K, max(0, x0):x0 + 2 * R * K]
            t = cv2.copyMakeBorder(t, 0, 2 * R * K - t.shape[0], 0, 2 * R * K - t.shape[1], cv2.BORDER_CONSTANT)
            row.append(t)
        r = np.hstack(row)
        cv2.putText(r, f"{post} {f['id']}", (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
        tiles.append(r)
cv2.imwrite("/tmp/claude-0/-home-user/0c8a008e-acb8-50fa-b850-2737be83dd04/scratchpad/corners.png", np.vstack(tiles))
