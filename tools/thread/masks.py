"""Foreground masks of the latest six posts (what must stay untouched), at 1080x1350:
  01-03  the foreground matte of tools/posts0103/compose0103.py (work/posts0103/POST_0X_matte.png)
  04-06  final post vs its own background render (tools/rebuild/compose.background): every
         pixel that differs is content (prints, type, patches, dashes, shadows of prints)
-> work/thread/POST_0X_fg.png  (0 = background, 255 = content)
   work/thread/occupancy_grid.png  the six panels as the profile grid shows them (planning)"""
import sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild")); sys.path.insert(0, str(ROOT / "tools/posts0103"))
import compose as C
import compose0103 as P
W = ROOT / "work/thread"
FINAL = {**{p: ROOT / "export/posts01-03_striped_1080x1350" / f"{p}.png" for p in ("POST_01", "POST_02", "POST_03")},
         **{p: ROOT / "export/rebuild_1080x1350" / f"{p}.png" for p in ("POST_04", "POST_05", "POST_06")}}

def fg_mask(post):
    if post in P.PANEL_X:
        m = cv2.imread(str(ROOT / "work/posts0103" / f"{post}_matte.png"), 0).astype(np.float32) / 255
        return np.clip(P.to_canvas(m, post, cv2.INTER_LINEAR), 0, 1)
    grain = cv2.cvtColor(cv2.imread("/home/user/jacketportable/public/assets/texture/grain-soft-240.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32)
    bg, _ = C.background(post, grain)
    fin = cv2.cvtColor(cv2.imread(str(FINAL[post])), cv2.COLOR_BGR2RGB).astype(np.float32)
    d = np.abs(fin - np.clip(bg, 0, 255).round()).max(2)
    return np.clip((d - 2) / 10, 0, 1)

if __name__ == "__main__":
    W.mkdir(parents=True, exist_ok=True)
    rows = []
    for post in FINAL:
        m = fg_mask(post)
        cv2.imwrite(str(W / f"{post}_fg.png"), (m * 255).round().astype(np.uint8))
        print(post, "content share", round(float((m > 0.5).mean()), 3))
