"""Typography check: every text run's coverage in the rebuilt post (sampled back to
grid-panel scale) against the original grid. -> export/rebuild_1080x1350/report.json"""
import json, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
import compose as C, fit_text as F
from text_runs import RUNS
g = cv2.cvtColor(cv2.imread(str(ROOT / "source/grid_preview_original.webp")), cv2.COLOR_BGR2RGB)
rep = {}
for post, runs in RUNS.items():
    r = cv2.cvtColor(cv2.imread(str(ROOT / "export/rebuild_1080x1350" / f"{post}.png")), cv2.COLOR_BGR2RGB)
    Wp = C.PANEL_W[post]
    Minv = np.float32([[C.S, 0, C.ox(post)], [0, C.S, 0]])
    small = cv2.warpAffine(cv2.GaussianBlur(r, (0, 0), 0.6), Minv, (Wp, 888), flags=cv2.WARP_INVERSE_MAP | cv2.INTER_AREA)
    orig = g[:, F.PANEL_X[post]:F.PANEL_X[post] + Wp]
    rep[post] = {}
    for run in runs:
        a = F.coverage(orig, run["box"], run["colour"]) > 0.5
        b = F.coverage(small, run["box"], run["colour"]) > 0.5
        rep[post][run["id"]] = dict(text=run["text"], iou=round(float((a & b).sum() / max((a | b).sum(), 1)), 4))
    print(post, {k: v["iou"] for k, v in rep[post].items()})
(ROOT / "export/rebuild_1080x1350/report_text.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False))
