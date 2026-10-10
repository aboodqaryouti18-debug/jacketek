import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; W = ROOT / "work/replace_photos"
P = cv2.imread(str(ROOT / "export/website_embroidery/POST_06_website_embroidery.png"))
R = cv2.imread(str(ROOT / "source/renders/06_collar.png"))
pg = cv2.GaussianBlur(cv2.cvtColor(P, cv2.COLOR_BGR2GRAY), (0, 0), 1.2).astype(np.float32) / 255
best = None
for s in (0.43, 0.445, 0.46):
  for ang in (-5, -4, -3):
    for tx in (308, 313, 318):
      for ty in (405, 412, 419):
        a = np.radians(ang); M = np.float32([[s*np.cos(a), -s*np.sin(a), tx], [s*np.sin(a), s*np.cos(a), ty]])
        Rg = cv2.GaussianBlur(cv2.cvtColor(R, cv2.COLOR_BGR2GRAY), (0, 0), 1.2 / s).astype(np.float32) / 255
        try:
            cc, M2 = cv2.findTransformECC(Rg, pg, M.copy(), cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), None, 1)
        except cv2.error: continue
        if best is None or cc > best[0]: best = (cc, M2)
cc, M = best; h, w = R.shape[:2]
corners = cv2.transform(np.float32([[[0, 0], [w, 0], [w, h], [0, h]]]), M)[0]
print("ECC", round(cc, 4), "scale", round(float(np.hypot(M[0,0], M[1,0])), 4), corners.round(1).tolist())
L = json.loads((W / "locate.json").read_text()); L["POST_06_collar"] = dict(render="06_collar.png", ecc=float(cc), M=M.tolist(), corners=corners.tolist(), size=[w, h])
(W / "locate.json").write_text(json.dumps(L, indent=1))
