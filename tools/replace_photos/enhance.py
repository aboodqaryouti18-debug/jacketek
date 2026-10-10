"""Shadows + background depth, applied ONLY to background pixels (text, red words,
photos, frames and cards are never modified). One light direction (top-left) and the
same shadow settings on all three posts, so the grid reads as one set."""
import json, sys, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; W = ROOT / "work/replace_photos"
sys.path.insert(0, str(ROOT / "tools")); from background_treatment import background_weight
OUT = ROOT / "export/photo_update"; OUT.mkdir(parents=True, exist_ok=True)
L = json.loads((W / "locate.json").read_text())
STYLE = {"POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}
LIGHT = np.array([0.6, 1.0]); LIGHT = LIGHT / np.linalg.norm(LIGHT)   # shadows fall right/down
SH = {"beige": dict(drop=0.20, contact=0.22, grad=0.035), "navy": dict(drop=0.38, contact=0.30, grad=0.05)}
DROP_OFF, DROP_SIG, CON_OFF, CON_SIG = 11, 11, 2.0, 2.2
def shift(m, d):
    return cv2.warpAffine(m, np.float32([[1, 0, d * LIGHT[0]], [0, 1, d * LIGHT[1]]]), m.shape[::-1])
outs, befores, report = [], [], {}
for post in ("POST_04", "POST_05", "POST_06"):
    before = cv2.imread(str(ROOT / f"export/website_embroidery/{post}_website_embroidery.png"))
    img = cv2.imread(str(W / "step1_photos" / f"{post}.png")); H, Wd = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    bg = background_weight(rgb, STYLE[post]).astype(np.float32)          # 0..1 background
    photos = np.zeros((H, Wd), np.uint8)
    for p, s, e, r, n in L["SLOTS"]:
        if p == post: photos |= (cv2.imread(str(W / e["slot_mask"]), 0) > 0)
    if post == "POST_06":   # the JK chest photo (kept): its window from the original match
        e = [x for x in L["POST_06"] if x["render"] == "chest"][0]
        q = np.zeros((H, Wd), np.uint8); cv2.fillPoly(q, [np.int32(np.round(e["corners"]))], 1); photos |= q
    if post == "POST_05": photos |= (cv2.imread(str(W / "POST_05_cards.png"), 0) > 0)
    # prints = non-background components that contain a photo/card (text components don't)
    # prints = white polaroid frames (+ the photos / cards they hold); the design's own soft
    # shadows next to them stay background, so the added shadow continues them smoothly
    frame = (rgb.min(2) > 226) & (rgb[..., 2] > 228)
    obj = (frame | (photos > 0)).astype(np.uint8)
    obj = cv2.morphologyEx(obj, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(obj)
    prints = np.zeros((H, Wd), np.float32)
    for i in range(1, n):
        comp = lab == i
        if st[i, cv2.CC_STAT_AREA] > 12000 and (photos[comp] > 0).sum() > 500: prints[comp] = 1
    # include the frames' anti-aliased rim, and keep the mask edge soft (no stair-steps)
    prints = cv2.GaussianBlur(prints, (0, 0), 0.7)
    # text / red words / graphics = non-background pixels that are not part of a print: protected
    # text / red words / graphics: pixels whose HUE differs from the background (shadows only
    # change lightness, so they stay background); every such pixel outside the prints is protected
    ref = {"beige": (253, 239, 212), "navy": (0, 48, 72)}[STYLE[post]]
    a = rgb.astype(np.float32); c1, c2 = a[..., 0] - a[..., 2], a[..., 1] - a[..., 2]
    chroma = np.sqrt((c1 - (ref[0] - ref[2])) ** 2 + (c2 - (ref[1] - ref[2])) ** 2)
    lumd = np.abs(a.mean(2) - sum(ref) / 3)
    text = (((chroma > 14) | (lumd > 70)) & (prints < 0.5)).astype(np.uint8)
    text = cv2.dilate(text, np.ones((5, 5), np.uint8)).astype(np.float32)
    cfg = SH[STYLE[post]]
    drop = cv2.GaussianBlur(shift(prints, DROP_OFF), (0, 0), DROP_SIG)
    contact = cv2.GaussianBlur(shift(prints, CON_OFF), (0, 0), CON_SIG)
    shade = (1 - cfg["drop"] * drop) * (1 - cfg["contact"] * contact)
    # gentle light across the whole post: brighter top-left, softer bottom-right
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
    t = ((xx / Wd) * LIGHT[0] + (yy / H) * LIGHT[1]) / LIGHT.sum()
    sweep = 1 + cfg["grad"] * (0.5 - t) * 2 * 0.5
    gain = shade * sweep
    w = np.clip(1 - prints, 0, 1) * np.clip(1 - text, 0, 1)                 # background pixels only
    eff = 1 + (gain - 1) * w
    out = np.clip(img.astype(np.float32) * eff[..., None], 0, 255).round().astype(np.uint8)
    cv2.imwrite(str(OUT / f"{post}.png"), out)
    # protected pixels: everything that is not background must be identical to step 1
    prot = w < 1e-3
    report_text = int((text > 0.5).sum())
    report[post] = dict(protected_px_changed=int((np.abs(out.astype(int) - img.astype(int)).max(2)[prot] > 0).sum()),
                        prints_px=int(prints.sum()), text_px=report_text)
    outs.append(out); befores.append(before)
grid = np.hstack(outs); cv2.imwrite(str(OUT / "grid_preview.png"), grid)
ba = np.vstack([np.hstack(befores), np.full((20, grid.shape[1], 3), 255, np.uint8), grid])
cv2.imwrite(str(OUT / "grid_before_after.jpg"), ba, [cv2.IMWRITE_JPEG_QUALITY, 92])
(OUT / "report.json").write_text(json.dumps(report, indent=1)); print(report)
