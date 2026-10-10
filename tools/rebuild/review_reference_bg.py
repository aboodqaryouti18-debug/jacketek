"""Review of the reference-background versions (export/reference_bg_1080x1350):
  grid_with_reference.jpg   posts 01-03 (reference) above 04-06, as they sit on the profile
  compare_POST_0X.jpg       approved rebuild | reference background
  work/rebuild/crops_refbg_POST_0X.png   100% crops (approved rebuild | new)"""
import sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
import compose as C
OUT = ROOT / "export/reference_bg_1080x1350"
CROPS = {"POST_04": [(0, 0, 330, 230), (380, 560, 667, 760), (20, 520, 340, 720)],
         "POST_05": [(0, 0, 330, 300), (0, 740, 330, 888), (600, 480, 666, 640)],
         "POST_06": [(0, 0, 330, 140), (0, 680, 330, 888), (300, 600, 667, 888)]}
if __name__ == "__main__":
    new = [cv2.imread(str(OUT / f"{p}.png")) for p in ("POST_04", "POST_05", "POST_06")]
    old = [cv2.imread(str(ROOT / "export/rebuild_1080x1350" / f"{p}.png")) for p in ("POST_04", "POST_05", "POST_06")]
    ref = cv2.imread(str(ROOT / "source/embroidery_reference_posts01-03.webp"))
    # the profile shows the centre 3:4 of each post: crop, then stack under the reference row
    x0 = int(round(C.ox("POST_04"))); w = 1080 - 2 * x0
    row = np.hstack([cv2.resize(n[:, x0:x0 + w], (667, 888), interpolation=cv2.INTER_AREA) for n in new])[:, :2000]
    cv2.imwrite(str(OUT / "grid_with_reference.jpg"), np.vstack([ref, np.full((8, 2000, 3), 255, np.uint8), row]), [cv2.IMWRITE_JPEG_QUALITY, 93])
    cv2.imwrite(str(OUT / "grid_preview.png"), np.hstack(new))
    for p, a, b in zip(("POST_04", "POST_05", "POST_06"), old, new):
        cv2.imwrite(str(OUT / f"compare_{p}.jpg"), np.hstack([a, np.full((1350, 16, 3), 255, np.uint8), b]), [cv2.IMWRITE_JPEG_QUALITY, 93])
        rows = []
        for (px0, py0, px1, py1) in CROPS[p]:
            X0, Y0 = int(round(C.ox(p) + px0 * C.S)), int(round(py0 * C.S)); X1, Y1 = int(round(C.ox(p) + px1 * C.S)), int(round(py1 * C.S))
            X0 = max(X0, 0); X1 = min(X1, 1080); Y1 = min(Y1, 1350)
            rows.append(np.hstack([a[Y0:Y1, X0:X1], np.full((Y1 - Y0, 10, 3), 255, np.uint8), b[Y0:Y1, X0:X1]]))
        wm = max(r.shape[1] for r in rows)
        rows = [cv2.copyMakeBorder(r, 0, 10, 0, wm - r.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r in rows]
        cv2.imwrite(str(ROOT / f"work/rebuild/crops_refbg_{p}.png"), np.vstack(rows))
