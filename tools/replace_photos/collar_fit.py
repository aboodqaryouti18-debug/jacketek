import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; W = ROOT / "work/replace_photos"
P = cv2.imread(str(ROOT / "export/website_embroidery/POST_06_website_embroidery.png"))
R = cv2.imread(str(ROOT / "source/renders/06_collar.png"))
pg = cv2.cvtColor(P, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
best = None; err=[None]
for s in np.linspace(0.40, 0.50, 11):
    for ang in (-8, -7, -6, -5):
        a = np.radians(ang); c, sn = s * np.cos(a), s * np.sin(a)
        for tx in (305, 315, 325):
            for ty in (420, 430, 440):
                M = np.float32([[c, -sn, tx], [sn, c, ty]])
                Rb = cv2.GaussianBlur(R, (0, 0), 0.45 / s)
                # ECC refine: warp post into render frame is what ECC estimates; use inverse
                Rg = cv2.cvtColor(Rb, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
                try:
                    cc, M2 = cv2.findTransformECC(Rg, pg, M.copy(), cv2.MOTION_AFFINE,
                                                  (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
                except cv2.error as e:
                    err[0] = str(e)[-120:]; continue
                if best is None or cc > best[0]: best = (cc, M2)
print('last err', err[0]); cc, M = best
print("ECC corr", round(cc, 4), "M", M.round(4).tolist())
h, w = R.shape[:2]; corners = cv2.transform(np.float32([[[0, 0], [w, 0], [w, h], [0, h]]]), M)[0]
L = json.loads((W / "locate.json").read_text()); L["POST_06_collar"] = dict(render="06_collar.png", ecc=float(cc), M=M.tolist(), corners=corners.tolist(), size=[w, h])
(W / "locate.json").write_text(json.dumps(L, indent=1)); print(corners.round(1).tolist())
