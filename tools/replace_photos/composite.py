"""Place each new photo into its slot with the original render's exact transform,
only inside the visible-photo mask (frames, cards, text and overlapping photos untouched)."""
import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; W = ROOT / "work/replace_photos"
NEW = ROOT / "source/new_photos"; OUT = ROOT / "work/replace_photos/step1_photos"; OUT.mkdir(parents=True, exist_ok=True)
L = json.loads((W / "locate.json").read_text())
posts = {n: cv2.imread(str(ROOT / f"export/website_embroidery/{n}_website_embroidery.png")) for n in ("POST_04", "POST_05", "POST_06")}
orig = {k: v.copy() for k, v in posts.items()}
# POST_05: the two UI cards occlude the photo; cut them out (cream card colour, largest regions, convex hull)
P5 = orig["POST_05"].astype(int); card = (np.abs(P5[..., 2] - 252) < 7) & (np.abs(P5[..., 1] - 240) < 7) & (np.abs(P5[..., 0] - 215) < 8)
n, lab, st, _ = cv2.connectedComponentsWithStats(card.astype(np.uint8))
cards = np.zeros(card.shape, np.uint8)
for i in np.argsort(-st[1:, cv2.CC_STAT_AREA])[:2] + 1:
    hull = cv2.convexHull(np.argwhere(lab == i)[:, ::-1].astype(np.int32)); cv2.fillPoly(cards, [hull], 1)
cards = cv2.dilate(cards, np.ones((5, 5), np.uint8))
cv2.imwrite(str(W / "POST_05_cards.png"), cards * 255)
order = ["big", "small", "front", "number", "collar"]   # back-to-front (small photo lies on the big one)
for post, slot, e, rf, nf in sorted(L["SLOTS"], key=lambda s: order.index(s[1])):
    P = posts[post]; H, Wd = P.shape[:2]
    new = cv2.imread(str(NEW / nf)); nh, nw = new.shape[:2]; rw, rh = e["size"]
    M = np.float64(e["M"]) @ np.array([[rw / nw, 0, 0], [0, rh / nh, 0], [0, 0, 1]])
    s = np.hypot(M[0, 0], M[1, 0])
    warp = cv2.warpAffine(cv2.GaussianBlur(new, (0, 0), 0.5 / s), M, (Wd, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    m = cv2.imread(str(W / e["slot_mask"]), 0).astype(np.float32) / 255
    if post == "POST_05": m *= (1 - cards)
    m = cv2.GaussianBlur(m, (0, 0), 0.6) * m.clip(0, 1) ** 0  # 1-px soft edge
    m = np.minimum(m, cv2.GaussianBlur(m, (0, 0), 0.6))
    P[:] = (P * (1 - m[..., None]) + warp * m[..., None]).round().astype(np.uint8)
    print(post, slot, nf, "scale", round(s, 3))
for k, v in posts.items():
    cv2.imwrite(str(OUT / f"{k}.png"), v)
    ch = np.abs(v.astype(int) - orig[k].astype(int)).max(2) > 0; print(k, "changed px", int(ch.sum()))
cv2.imwrite("/tmp/claude-0/-home-user/0c8a008e-acb8-50fa-b850-2737be83dd04/scratchpad/step1.jpg", np.hstack([posts[k] for k in ("POST_04", "POST_05", "POST_06")]))
