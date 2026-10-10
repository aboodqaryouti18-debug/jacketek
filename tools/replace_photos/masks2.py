"""Visible photo area per slot = where the warped original render agrees with the post
(smoothed), largest region, small holes filled. Collar: the measured frame window."""
import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; W = ROOT / "work/replace_photos"
L = json.loads((W / "locate.json").read_text())
# collar: window measured on the post (frame inner corners); photo = collar render, top-aligned, width-fit
win = np.float32([[316.2, 416.8], [578.2, 395.0], [587.5, 510.5], [326.2, 533.0]])
top = win[1] - win[0]; ang = np.arctan2(top[1], top[0]); s = np.hypot(*top) / 615
s = float(s); ang = float(ang)
L["POST_06_collar"] = dict(render="06_collar.png", M=[[s*np.cos(ang), -s*np.sin(ang), float(win[0][0])], [s*np.sin(ang), s*np.cos(ang), float(win[0][1])]],
                           window=win.tolist(), size=[615, 319])
SLOTS = [("POST_04", "big", [x for x in L["POST_04"] if x["render"] == "back"][0], "02_back.png", "back.webp"),
         ("POST_04", "small", L["POST_04_small"], "02_back.png", "back.webp"),
         ("POST_05", "front", [x for x in L["POST_05"] if x["render"] == "front"][0], "03_front_full.png", "front.webp"),
         ("POST_06", "number", [x for x in L["POST_06"] if x["render"] == "number"][0], "05_sleeve_number.png", "sleeve_number.webp"),
         ("POST_06", "collar", L["POST_06_collar"], "06_collar.png", "collar.webp")]
for post, slot, e, rf, nf in SLOTS:
    P = cv2.imread(str(ROOT / f"export/website_embroidery/{post}_website_embroidery.png")); H, Wd = P.shape[:2]
    if slot == "collar":
        m = np.zeros((H, Wd), np.uint8); cv2.fillPoly(m, [np.int32(np.round(win))], 1)
    else:
        R = cv2.imread(str(ROOT / "source/renders" / rf)); M = np.float32(e["M"]); sc = np.hypot(M[0, 0], M[1, 0])
        Wr = cv2.warpAffine(cv2.GaussianBlur(R, (0, 0), 0.45 / sc) if sc < 1 else R, M, (Wd, H))
        ins = cv2.erode(cv2.warpAffine(np.full(R.shape[:2], 255, np.uint8), M, (Wd, H), flags=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8))
        d = np.abs(Wr.astype(np.float32) - P.astype(np.float32)).max(2)
        ds = cv2.blur(d, (7, 7))
        m = ((ds < 22) & (ins > 0)).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        m = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
        inv = 1 - m; n, lab, st, _ = cv2.connectedComponentsWithStats(inv)
        for i in range(1, n):
            if st[i, cv2.CC_STAT_AREA] < 3000: m[lab == i] = 1   # small holes (letters, edges)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8)) & (ins > 0)
    e["new"] = nf; e["slot_mask"] = f"{post}_{slot}_mask.png"
    cv2.imwrite(str(W / e["slot_mask"]), m * 255)
    print(post, slot, "mask px", int(m.sum()))
L["SLOTS"] = [[p, s_, e, r, n] for p, s_, e, r, n in SLOTS]
(W / "locate.json").write_text(json.dumps(L, indent=1))
viz = []
for n in (4, 5, 6):
    P = cv2.imread(str(ROOT / f"export/website_embroidery/POST_0{n}_website_embroidery.png"))
    for p, s_, e, r, nf in SLOTS:
        if p == f"POST_0{n}":
            m = cv2.imread(str(W / e["slot_mask"]), 0) > 0; col = np.array([0, 255, 0]) if s_ in ("big", "front", "number") else np.array([255, 0, 255])
            P[m] = (0.55 * P[m] + 0.45 * col).astype(np.uint8)
    viz.append(P)
cv2.imwrite("/tmp/claude-0/-home-user/0c8a008e-acb8-50fa-b850-2737be83dd04/scratchpad/masks2.jpg", np.hstack(viz))
