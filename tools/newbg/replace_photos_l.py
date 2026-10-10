"""Posts 04-06: the jacket photos replaced with the five burgundy jacket photos
(source/new_photos_l), on the latest design (export/six_posts_new_background).
Everything else is the same build as tools/newbg/replace_background.py (supplied
background plate, shadows, frames, cards, type, embroidery, patches); only the photo
inside each print window changes. Each photo is cover-fitted into its window
(uniform scale, no stretch, no recolour; crop chosen per slot), mapped with the
window's own quad. Posts 01-03 are copied byte for byte.
-> export/six_posts_l_photos/"""
import json, shutil, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/newbg"))
import replace_background as RB
C = RB.C
SRC = ROOT / "source/new_photos_l"; OUT = ROOT / "export/six_posts_l_photos"
# slot: (file, crop centre (x, y) in source px, crop width in source px or None = widest that fits)
SLOTS = {
    ("POST_04", "big"):    ("back_l.webp", (1000, 565), None),          # back: SENIOR 2027 + cap
    ("POST_04", "small"):  ("hand_spider.webp", (1000, 800), 900),      # sleeve: the Spider-Man patch
    ("POST_05", "front"):  ("full_jacket_l.webp", (1000, 1000), None),  # the full front, main visual
    ("POST_06", "chest"):  ("chest_l.webp", (1000, 470), None),         # chest: "أنا Strong" + JK
    ("POST_06", "number"): ("09_l.webp", (592, 960), None),             # sleeve: 09
    ("POST_06", "collar"): ("full_jacket_l.webp", (1010, 240), 760),    # collar detail of the full front
}
FR = {p: {f["id"]: f for f in C.J("work/rebuild/frames.json")[p]} for p in ("POST_04", "POST_05", "POST_06")}

def crop_rect(shape, wq, c, cw):
    H, W = shape[:2]
    ww = (np.linalg.norm(wq[1] - wq[0]) + np.linalg.norm(wq[2] - wq[3])) / 2
    wh = (np.linalg.norm(wq[3] - wq[0]) + np.linalg.norm(wq[2] - wq[1])) / 2
    asp = ww / wh
    if cw is None: cw = min(W, H * asp)
    ch = cw / asp
    assert cw <= W + 0.5 and ch <= H + 0.5, "crop larger than the photo"
    x0 = float(np.clip(c[0] - cw / 2, 0, W - cw)); y0 = float(np.clip(c[1] - ch / 2, 0, H - ch))
    return np.float32([[x0, y0], [x0 + cw, y0], [x0 + cw, y0 + ch], [x0, y0 + ch]]), cw / ww

def photo_content(post, fid):
    if (post, fid) not in SLOTS: return ORIG(post, fid)
    fn, c, cw = SLOTS[(post, fid)]
    src = cv2.cvtColor(cv2.imread(str(SRC / fn)), cv2.COLOR_BGR2RGB).astype(np.float32)
    wq = np.array(FR[post][fid]["window"], np.float64)
    rect, k = crop_rect(src.shape, wq, c, cw)
    q = (np.c_[wq, np.ones(4)] @ C.A(post, C.SS).T)[:, :2].astype(np.float32)
    Hm = cv2.getPerspectiveTransform(rect, q)
    scale = np.sqrt(abs(np.linalg.det(Hm[:2, :2])))
    if scale < 1: src = cv2.GaussianBlur(src, (0, 0), 0.45 / scale)
    big = cv2.warpPerspective(src, Hm, (C.W_OUT * C.SS, C.H_OUT * C.SS), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return np.clip(C.down(big), 0, 255)

ORIG = C.photo_content
C.photo_content = photo_content

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    prev = ROOT / "export/six_posts_new_background"
    for p in ("POST_01", "POST_02", "POST_03"): shutil.copyfile(prev / f"{p}.png", OUT / f"{p}.png")
    for post in ("POST_04", "POST_05", "POST_06"):
        fg = cv2.imread(str(ROOT / "work/thread" / f"{post}_fg.png"), 0) / 255.0
        pl, _ = RB.plate(post, fg < 0.7)
        img = RB.post_0406(post, pl)
        cv2.imwrite(str(OUT / f"{post}.png"), cv2.cvtColor(np.clip(img, 0, 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
        print(post, "ok")
    full = [cv2.imread(str(OUT / f"POST_0{i}.png")) for i in range(1, 7)]
    grid = np.vstack([np.hstack(full[:3]), np.hstack(full[3:])])
    cv2.imwrite(str(OUT / "six_posts_full.png"), grid)
    cv2.imwrite(str(OUT / "six_posts_preview.jpg"), cv2.resize(grid, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
    # before | after for 04-06
    for p in ("POST_04", "POST_05", "POST_06"):
        a = cv2.imread(str(prev / f"{p}.png")); b = cv2.imread(str(OUT / f"{p}.png"))
        cv2.imwrite(str(OUT / f"compare_{p}.jpg"), np.hstack([a, np.full((1350, 16, 3), 255, np.uint8), b]), [cv2.IMWRITE_JPEG_QUALITY, 92])
