"""Visible-photo masks: where the warped original render matches the post pixels
(i.e. the photo is actually visible, not covered by frames, cards or text)."""
import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; W = ROOT / "work/replace_photos"
L = json.loads((W / "locate.json").read_text())
REN = {"back": "02_back.png", "front": "03_front_full.png", "chest": "04_chest_letters.png", "number": "05_sleeve_number.png"}
slots = [("POST_04", "big", [e for e in L["POST_04"] if e["render"] == "back"][0], "02_back.png"),
         ("POST_04", "small", L["POST_04_small"], "02_back.png"),
         ("POST_05", "front", [e for e in L["POST_05"] if e["render"] == "front"][0], "03_front_full.png"),
         ("POST_06", "chest", [e for e in L["POST_06"] if e["render"] == "chest"][0], "04_chest_letters.png"),
         ("POST_06", "number", [e for e in L["POST_06"] if e["render"] == "number"][0], "05_sleeve_number.png")]
res = {}
for post, slot, e, rf in slots:
    P = cv2.imread(str(ROOT / f"export/website_embroidery/{post}_website_embroidery.png")); H, Wd = P.shape[:2]
    R = cv2.imread(str(ROOT / "source/renders" / rf)); M = np.float32(e["M"])
    # area-correct downscale: blur by scale first
    s = np.hypot(M[0, 0], M[1, 0]); Rb = cv2.GaussianBlur(R, (0, 0), max(0.01, 0.45 / s)) if s < 1 else R
    warp = cv2.warpAffine(Rb, M, (Wd, H), flags=cv2.INTER_LINEAR)
    inside = cv2.warpAffine(np.full(R.shape[:2], 255, np.uint8), M, (Wd, H), flags=cv2.INTER_NEAREST)
    inside = cv2.erode(inside, np.ones((3, 3), np.uint8))
    d = np.abs(warp.astype(int) - P.astype(int)).max(2)
    vis = ((d < 40) & (inside > 0)).astype(np.uint8)
    vis = cv2.morphologyEx(vis, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    vis = cv2.morphologyEx(vis, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    # largest component only, holes filled (photo content such as white sleeves can differ slightly)
    n, lab, st, _ = cv2.connectedComponentsWithStats(vis)
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA])); vis = (lab == k).astype(np.uint8)
    cnts, _ = cv2.findContours(vis, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(vis); cv2.drawContours(filled, cnts, -1, 1, -1)
    # true occluders inside the filled area (text/cards) are kept out: they differ strongly from the render
    occl = (d > 70) & (filled > 0)
    occl = cv2.dilate(cv2.morphologyEx(occl.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8)), np.ones((3, 3), np.uint8))
    final = (filled > 0) & (occl == 0) & (inside > 0)
    cv2.imwrite(str(W / f"{post}_{slot}_mask.png"), final.astype(np.uint8) * 255)
    ov = P.copy(); ov[final] = (0.5 * ov[final] + 0.5 * np.array([0, 255, 0])).astype(np.uint8)
    cv2.imwrite(str(W / f"{post}_{slot}_overlay.jpg"), ov)
    res[f"{post}_{slot}"] = dict(pixels=int(final.sum()), median_diff_in_mask=float(np.median(d[final])), occluder_px=int((occl > 0).sum()))
    print(post, slot, res[f"{post}_{slot}"])
