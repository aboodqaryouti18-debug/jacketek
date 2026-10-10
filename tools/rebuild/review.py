"""Review sheets for the rebuilt posts:
  compare_POST_0X.jpg   approved (3:4 panel, shown at the same scale, centred) | rebuild 1080x1350
  crops_POST_0X.png     1:1 crops of the rebuild (100% zoom) next to the approved, same area
  grid_rebuild.png      the three rebuilt posts side by side"""
import sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
import compose as C
OUT = ROOT / "export/rebuild_1080x1350"
CROPS = {  # panel px boxes (x0, y0, x1, y1) of the areas to inspect at 100%
    "POST_04": [(200, 80, 560, 300), (30, 520, 330, 720), (150, 380, 330, 520), (140, 720, 480, 860)],
    "POST_05": [(330, 60, 650, 290), (340, 290, 650, 560), (340, 550, 650, 810), (40, 330, 360, 560), (300, 800, 650, 870)],
    "POST_06": [(60, 0, 340, 140), (60, 640, 320, 860), (330, 380, 630, 560), (300, 630, 667, 888)],
}
def approved_on_canvas(post):
    a = cv2.imread(str(ROOT / "export/patches" / f"{post}.png"))
    big = cv2.resize(a, None, fx=C.S, fy=C.S, interpolation=cv2.INTER_CUBIC)
    canvas = np.full((C.H_OUT, C.W_OUT, 3), 255, np.uint8)
    x0 = int(round(C.ox(post))); canvas[:, x0:x0 + big.shape[1]] = big[:C.H_OUT, :C.W_OUT - x0]
    return canvas
if __name__ == "__main__":
    grid = []
    for post in ("POST_04", "POST_05", "POST_06"):
        r = cv2.imread(str(OUT / f"{post}.png")); grid.append(r)
        a = approved_on_canvas(post)
        lab = lambda im, t: cv2.putText(im.copy(), t, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (40, 40, 200), 2)
        cv2.imwrite(str(OUT / f"compare_{post}.jpg"), np.hstack([lab(a, "approved (667x888 grid panel, enlarged)"), np.full((C.H_OUT, 16, 3), 255, np.uint8), lab(r, "rebuilt 1080x1350")]), [cv2.IMWRITE_JPEG_QUALITY, 93])
        rows = []
        for (x0, y0, x1, y1) in CROPS[post]:
            X0, Y0 = int(round(C.ox(post) + x0 * C.S)), int(round(y0 * C.S)); X1, Y1 = int(round(C.ox(post) + x1 * C.S)), int(round(y1 * C.S))
            rows.append(np.hstack([a[Y0:Y1, X0:X1], np.full((Y1 - Y0, 10, 3), 255, np.uint8), r[Y0:Y1, X0:X1]]))
        wmax = max(x.shape[1] for x in rows)
        rows = [cv2.copyMakeBorder(x, 0, 10, 0, wmax - x.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for x in rows]
        cv2.imwrite(str(ROOT / "work/rebuild" / f"crops_{post}.png"), np.vstack(rows))
    cv2.imwrite(str(OUT / "grid_rebuild.png"), np.hstack(grid))
