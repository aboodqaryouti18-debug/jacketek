import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; W = ROOT / "work/replace_photos"
L = json.loads((W / "locate.json").read_text())
def warp_render(post, rf, M):
    P = cv2.imread(str(ROOT / f"export/website_embroidery/{post}_website_embroidery.png")); H, Wd = P.shape[:2]
    R = cv2.imread(str(ROOT / "source/renders" / rf)); M = np.float32(M); s = np.hypot(M[0, 0], M[1, 0])
    Rb = cv2.GaussianBlur(R, (0, 0), 0.45 / s) if s < 1 else R
    return P, cv2.warpAffine(Rb, M, (Wd, H)), cv2.warpAffine(np.full(R.shape[:2], 255, np.uint8), M, (Wd, H), flags=cv2.INTER_NEAREST)
rows = []
for post, slot, e, rf in [("POST_04","big",[x for x in L["POST_04"] if x["render"]=="back"][0],"02_back.png"),
                          ("POST_04","small",L["POST_04_small"],"02_back.png"),
                          ("POST_05","front",[x for x in L["POST_05"] if x["render"]=="front"][0],"03_front_full.png"),
                          ("POST_06","number",[x for x in L["POST_06"] if x["render"]=="number"][0],"05_sleeve_number.png"),
                          ("POST_06","collar",L["POST_06_collar"],"06_collar.png")]:
    P, Wr, ins = warp_render(post, rf, e["M"])
    d = np.abs(Wr.astype(int) - P.astype(int)).max(2); d[ins == 0] = 0
    v = np.clip(d * 4, 0, 255).astype(np.uint8)
    rows.append(cv2.putText(cv2.cvtColor(v, cv2.COLOR_GRAY2BGR), f"{post} {slot}", (10, 30), 0, 0.8, (0, 0, 255), 2))
cv2.imwrite("/tmp/claude-0/-home-user/0c8a008e-acb8-50fa-b850-2737be83dd04/scratchpad/dmaps.jpg", np.hstack(rows))
