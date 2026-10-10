"""Replace the backgrounds of the six posts with the supplied background image
(source/background_supplied.jpg), used directly: its pixels, not a redraw.

  plate     each panel of the supplied image (panels x 0|425|855|1280, y 0|531|1065:
            six 4:5 posts) resampled to 1080 x 1350 (Lanczos, no sharpening). The panel
            edges are the post edges, so the dots and the thread meet across every boundary.
            Where the supplied image shows its own content (photos, type, stickers) instead
            of background, and that spot is exposed in our post, the plate takes the
            supplied image's own background pixels one or more dot-grid steps away
            (78.25 x 75.25 px), so dot phase and colour stay the image's own.
  posts     the old background is removed completely (plain colour, stripes, website glow,
            previous dots / threads, the old dashed guide lines) and the foreground is
            composited on the plate with its own shadows:
              04-06  re-composed from their layers (tools/rebuild/compose.py): plate x the
                     prints' shadows, then prints, type, embroidery, patches (unchanged)
              01-03  their foreground matte (tools/posts0103/compose0103.py) on plate x the
                     design's shadow layer; the old dashed guides are taken out of the matte
-> export/six_posts_new_background/"""
import json, sys
from pathlib import Path
import cv2, numpy as np
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild")); sys.path.insert(0, str(ROOT / "tools/posts0103"))
import compose as C
import compose0103 as P3
SRC = ROOT / "source/background_supplied.jpg"
OUT = ROOT / "export/six_posts_new_background"; WK = ROOT / "work/newbg"
XB, YB = [0, 425, 855, 1280], [0, 531, 1065]
POS = {"POST_01": (0, 0), "POST_02": (1, 0), "POST_03": (2, 0), "POST_04": (0, 1), "POST_05": (1, 1), "POST_06": (2, 1)}
STYLE = {"POST_01": "navy", "POST_02": "beige", "POST_03": "navy", "POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}
STEP = (78.25, 75.25)
LUM = np.float32([0.299, 0.587, 0.114])

def plate_raw(post):
    c, r = POS[post]
    a = cv2.cvtColor(cv2.imread(str(SRC)), cv2.COLOR_BGR2RGB).astype(np.float32)
    p = a[YB[r]:YB[r + 1], XB[c]:XB[c + 1]]
    return np.clip(cv2.resize(p, (1080, 1350), interpolation=cv2.INTER_LANCZOS4), 0, 255)

THREAD = None
def thread_mask(post):
    """the supplied image's own thread: within 9 px of its traced stretches (work/trace/route.json)"""
    global THREAD
    if THREAD is None:
        R = json.loads((ROOT / "work/trace/route.json").read_text())
        THREAD = np.zeros((2700, 3240), np.uint8)
        for v in R.values():
            cv2.polylines(THREAD, [np.int32(np.round(np.array(v["points"]) * 4))], False, 1, 19, cv2.LINE_8, shift=2)
    c, r = POS[post]
    return THREAD[r * 1350:(r + 1) * 1350, c * 1080:(c + 1) * 1080] > 0

def plate_bg_mask(post, pl):
    """where the supplied image shows background (its navy / beige surface, its dots, its thread):
    large content by colour (median 31), thin content (its lettering, dashes of its type, sticker
    outlines) as strong local contrast that is neither its thread nor one of its small dots"""
    sm = cv2.medianBlur(pl.astype(np.uint8), 31).astype(np.float32); lum = sm @ LUM
    if STYLE[post] == "navy": bg = (lum < 75) & (sm[..., 2] - sm[..., 0] > 25)
    else: bg = (lum > 190) & (sm[..., 0] - sm[..., 2] > 18) & (sm[..., 0] - sm[..., 2] < 60)
    dev = np.abs(pl @ LUM - lum)
    th = thread_mask(post)
    strong = (dev > 38).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(strong)
    dots = np.zeros_like(strong, bool)
    small = (st[:, cv2.CC_STAT_AREA] <= 40) & (st[:, cv2.CC_STAT_WIDTH] <= 9) & (st[:, cv2.CC_STAT_HEIGHT] <= 9)
    small[0] = False
    dots = small[lab]
    thin = strong.astype(bool) & ~th & ~dots
    thin = cv2.dilate(thin.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))) > 0
    bg = (cv2.erode(bg.astype(np.uint8), np.ones((9, 9))) > 0) & ~thin
    return bg, bg & ~th

def plate(post, need):
    """the supplied panel; where it has content but `need` (our exposed background) says the
    plate shows, copy its own clean background from k dot steps away (nearest first)"""
    pl = plate_raw(post)
    bg, clean = plate_bg_mask(post, pl)
    hole = need & ~bg
    hole = cv2.dilate(hole.astype(np.uint8), np.ones((5, 5))).astype(bool) & ~bg | hole
    filled = np.zeros_like(hole)
    out = pl.copy()
    yy, xx = np.mgrid[0:1350, 0:1080].astype(np.float32)
    offs = sorted({(i, j) for i in range(-6, 7) for j in range(-6, 7) if (i, j) != (0, 0)}, key=lambda t: t[0] ** 2 + t[1] ** 2)
    for i, j in offs:
        todo = hole & ~filled
        if not todo.any(): break
        mx, my = xx + i * STEP[0], yy + j * STEP[1]
        ok = cv2.remap(clean.astype(np.float32), mx, my, cv2.INTER_NEAREST, borderValue=0) > 0.5
        take = todo & ok
        if take.any():
            src = cv2.remap(pl, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            out[take] = src[take]; filled |= take
    # soft seams at the fill edge
    m = cv2.GaussianBlur(filled.astype(np.float32), (0, 0), 1.0)[..., None]
    out = pl * (1 - m) + out * m
    return out, dict(hole_px=int(hole.sum()), unfilled_px=int((hole & ~filled).sum()))

def post_0406(post, pl):
    grain = cv2.cvtColor(cv2.imread("/home/user/jacketportable/public/assets/texture/grain-soft-240.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32)
    style = C.STYLE[post]
    Pm = C.prints_union(post)
    img = pl * (C.design_shadow(Pm, style) * C.enhance_shadow(Pm, post, sweep_on=False))[..., None]
    img = C.prints_layers(post, img)
    img = C.text_layers(post, img)
    # the patches keep their approved look: their light is read from the approved composite
    w, _ = C.background(post, grain); d_rgb, d_a = C.dashes_layer(post)
    light = C.text_layers(post, C.prints_layers(post, C.over(w, d_rgb, d_a)))
    return C.patches_layer(post, img, light)

def strip_dashes(post, p, a):
    """the old dashed guides out of the 01-03 matte: small elongated marks in the guide colour"""
    nav = STYLE[post] == "navy"
    L = p @ LUM; col = (L > 150) if nav else (L < 90)
    redish = (p[..., 0] - p[..., 2] > 60)
    m = (a > 0.3) & col & ~redish
    lab, n = ndi.label(m)
    alab, an = ndi.label(a > 0.3)
    sizes = ndi.sum(np.ones_like(a), alab, range(1, an + 1))
    large = np.isin(alab, 1 + np.flatnonzero(sizes > 80))      # type, prints, stickers
    big = ndi.binary_dilation(large & ~m, iterations=1)
    cand = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == i; area = comp.sum()
        if not (5 <= area <= 45): continue
        ys, xs = np.nonzero(comp)
        if len(xs) < 3: continue
        ev, evec = np.linalg.eigh(np.cov(np.c_[xs, ys].T))
        if ev[1] / max(ev[0], 0.05) < 4: continue                 # elongated
        if (big[sl] & comp).any(): continue                        # touching type / prints
        cand.append((i, sl, np.array([xs.mean() + sl[1].start, ys.mean() + sl[0].start]), evec[:, 1]))
    # only marks in a dashed LINE: link two marks when they are 12-24 px apart and both point
    # along the segment between them; a chain of >= 3 linked marks is a dashed guide
    kill = np.zeros_like(m)
    k = len(cand); parent = list(range(k))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for u in range(k):
        for w in range(u + 1, k):
            v = cand[w][2] - cand[u][2]; dist = np.hypot(*v)
            if not (12 < dist < 24): continue
            v = v / dist
            if abs(v @ cand[u][3]) > 0.9 and abs(v @ cand[w][3]) > 0.9:
                parent[find(u)] = find(w)
    groups = {}
    for u in range(k): groups.setdefault(find(u), []).append(u)
    for g in groups.values():
        if len(g) >= 3:
            for u in g:
                i, sl, _, _ = cand[u]; kill[sl] |= lab[sl] == i
    kill = ndi.binary_dilation(kill, iterations=1) & (a > 0)
    a2 = a.copy(); a2[kill] = 0
    return a2, int(ndi.label(kill)[1])

def post_0103(post, pl):
    p, a, shade, _ = P3.split(post)
    a, ndash = strip_dashes(post, p, a)
    # the old grid's panel seams leak into the shadow layer at the panel edges: not a shadow
    ramp = np.clip((np.minimum(np.arange(shade.shape[1]), shade.shape[1] - 1 - np.arange(shade.shape[1])) - 4) / 4, 0, 1)
    shade = 1 + (shade - 1) * ramp[None, :]
    sh = P3.to_canvas(shade - 1, post, cv2.INTER_LINEAR) + 1
    out = pl * sh[..., None]
    fa = np.clip(P3.to_canvas(a, post, cv2.INTER_LANCZOS4), 0, 1)
    fc = np.clip(P3.to_canvas(p * a[..., None], post, cv2.INTER_LANCZOS4), 0, 255)
    fc = np.clip(fc + P3.SHARPEN * (fc - cv2.GaussianBlur(fc, (0, 0), 1.1)), 0, 255)
    return fc + out * (1 - fa[..., None]), ndash

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True); WK.mkdir(parents=True, exist_ok=True)
    rep = {}
    for post in POS:
        fg = cv2.imread(str(ROOT / "work/thread" / f"{post}_fg.png"), 0) / 255.0
        need = fg < 0.7
        pl, info = plate(post, need)
        cv2.imwrite(str(WK / f"{post}_plate.png"), cv2.cvtColor(pl.round().astype(np.uint8), cv2.COLOR_RGB2BGR))
        if post in ("POST_04", "POST_05", "POST_06"): img = post_0406(post, pl); info["old_dash_marks_removed"] = "dash layer not composed"
        else: img, nd = post_0103(post, pl); info["old_dash_marks_removed"] = nd
        cv2.imwrite(str(OUT / f"{post}.png"), cv2.cvtColor(np.clip(img, 0, 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
        rep[post] = info; print(post, info)
    full = [cv2.imread(str(OUT / f"{p}.png")) for p in POS]
    grid = np.vstack([np.hstack(full[:3]), np.hstack(full[3:])])
    cv2.imwrite(str(OUT / "six_posts_full.png"), grid)
    cv2.imwrite(str(OUT / "six_posts_preview.jpg"), cv2.resize(grid, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
    (OUT / "report.json").write_text(json.dumps(rep, indent=1))
