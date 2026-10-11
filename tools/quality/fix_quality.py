"""Quality pass on the six approved posts (export/final_instagram, untouched) -> export/quality_fixed.

Causes found (100% inspection):
  01-03  the cut-out matte was computed at the grid's 667 px, nearly binary
         (smoothstep 7..24), then Lanczos-enlarged 1.52x: edges stair-stepped by 1-2 px,
         and the edge pixels still carried the OLD background colour (halo rims: most
         visible on the beige of 02, where the old beige != the new plate's beige).
         The 0.35 unsharp mask was applied to the premultiplied layer, so it also
         sharpened those rims.
  03     the JK patch used a binary colour-threshold mask of the old F patch: ragged,
         aliased outline, and slivers of the old navy patch left outside it.
  04-06  rendered from the full-res sources at 2x supersampling: edges clean, unchanged.

Fixes:
  01-03  alpha re-estimated at the final 1080x1350 from the enlarged artwork against the
         enlarged old background (x its shadow layer), limited to a 3 px band around the
         original matte (no new pixels, the dashed-guide removal kept); solid interiors
         from the original matte. Edge colours decontaminated (F = (P - (1-a) B_old) / a),
         sharpening applied to the decontaminated colour, not across the edge.
  03     the JK patch drawn as a supersampled (4x) polygon on its measured quad, expanded
         to cover the old patch's footprint completely; a soft contact shadow (light from
         the top left, as the design's other shadows) under its new edge.
Posts 04-06: copied unchanged."""
import shutil, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/newbg"))
import replace_background as RB
P3 = RB.P3
SRC = ROOT / "export/final_instagram"; OUT = ROOT / "export/quality_fixed"

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

def post_0103_fixed(post, pl):
    p, a0, shade, bg = P3.split(post)
    a, _ = RB.strip_dashes(post, p, a0)
    # the removed dashed guides (and their 1-px fringe the old pipeline left): never foreground
    killed = cv2.dilate(((a0 > 0.2) & (a < 0.05)).astype(np.uint8), np.ones((5, 5))) > 0
    a = np.where(killed & (a < 0.9), 0, a).astype(np.float32)
    ramp = np.clip((np.minimum(np.arange(shade.shape[1]), shade.shape[1] - 1 - np.arange(shade.shape[1])) - 4) / 4, 0, 1)
    shade_r = 1 + (shade - 1) * ramp[None, :]
    up = lambda x, i=cv2.INTER_LANCZOS4: P3.to_canvas(x, post, i)
    P = np.clip(up(p), 0, 255)                                         # the artwork, enlarged
    Bold = np.clip(up(bg, cv2.INTER_LINEAR) * (up(shade - 1, cv2.INTER_LINEAR) + 1)[..., None], 0, 255)
    a_up = np.clip(up(a, cv2.INTER_LINEAR), 0, 1)
    # alpha at final resolution: colour distance to the old background, in a band around the matte
    resid = np.abs(P - (P @ RB.LUM / np.maximum(Bold @ RB.LUM, 1)).clip(0, 1.2)[..., None] * Bold).max(2)
    a_hi = smoothstep(7, 24, cv2.GaussianBlur(resid, (0, 0), 0.5))
    band = cv2.dilate((a_up > 0.02).astype(np.uint8), np.ones((7, 7))) > 0
    core = cv2.erode((a_up > 0.98).astype(np.uint8), np.ones((5, 5))) > 0
    A = np.where(core, 1.0, a_hi * band)
    A = np.maximum(A, np.where(cv2.erode((a_up > 0.5).astype(np.uint8), np.ones((3, 3))) > 0, a_up, 0))
    # outside the panel: nothing
    inside = up(np.ones_like(a), cv2.INTER_NEAREST) > 0.5
    A = (A * inside * (up(killed.astype(np.float32), cv2.INTER_LINEAR) < 0.01)).astype(np.float32)
    if post == "POST_02":
        A, P = straight_frame_edges(post, A, P)
    # decontaminate edge colours, then sharpen the colour (not the edge)
    Aa = np.maximum(A, 1e-3)[..., None]
    F = np.where(A[..., None] > 0.05, (P - (1 - A[..., None]) * Bold) / Aa, P)
    F = np.clip(F, 0, 255)
    F = np.clip(F + P3.SHARPEN * (F - cv2.GaussianBlur(F, (0, 0), 1.1)), 0, 255)
    sh = up(shade_r - 1, cv2.INTER_LINEAR) + 1
    out = F * A[..., None] + pl * sh[..., None] * (1 - A[..., None])
    return out, A

FRAME_WHITE = np.float32([255, 253, 245])
STICKERS_02 = [(25, 45, 145, 195), (545, 75, 640, 195)]      # panel px boxes: the two stickers on the big print

def straight_frame_edges(post, A, P):
    """02's three polaroids: the matte's ragged outer edge (from the 667 px source) replaced
    by their measured straight edges (work/quality_frames_post02.json), supersampled 4x"""
    import json
    F = json.loads((ROOT / "work/quality_frames_post02.json").read_text())
    K = 4; mk = np.zeros((1350 * K, 1080 * K), np.uint8)
    for f in F:
        q = (np.c_[np.array(f["outer"]), np.ones(4)] @ P3.C.A(post, K).T)[:, :2]
        cv2.fillPoly(mk, [np.int32(np.round(q * 16))], 255, cv2.LINE_AA, shift=4)
    U = cv2.resize(mk.astype(np.float32) / 255, (1080, 1350), interpolation=cv2.INTER_AREA)
    edge = (U > 0.003) & (U < 0.997)
    band = cv2.dilate(edge.astype(np.uint8), np.ones((7, 7))) > 0
    keep = np.zeros_like(band)
    for x0, y0, x1, y1 in STICKERS_02:
        X0, Y0 = int(P3.C.ox(post) + x0 * P3.C.S), int(y0 * P3.C.S); X1, Y1 = int(P3.C.ox(post) + x1 * P3.C.S), int(y1 * P3.C.S)
        keep[Y0:Y1, X0:X1] = True
    # the big print's bottom edge is hand-estimated (mostly hidden): leave that edge as it was
    big = np.array(F[0]["outer"]); bl, br = big[3], big[2]
    yy, xx = np.mgrid[0:1350, 0:1080].astype(np.float32)
    xp, yp = (xx - P3.C.ox(post)) / P3.C.S, yy / P3.C.S
    d = np.abs((br[0] - bl[0]) * (bl[1] - yp) - (bl[0] - xp) * (br[1] - bl[1])) / np.hypot(*(br - bl))
    keep |= d < 14
    sel = band & ~keep
    # inside the band: the polygon's coverage; colour = the frame's white where the matte had less
    newP = np.where((sel & (U > A))[..., None], FRAME_WHITE * U[..., None] + P * (1 - U[..., None]), P)
    A2 = np.where(sel, U, A)
    return A2.astype(np.float32), newP

def jk_patch(img):
    import replace_f_post03 as JK
    m = cv2.imread(str(ROOT / "work/newbg/POST_03_Fpatch_mask.png"), 0) > 127
    Q = JK.QUAD.astype(np.float64); c = Q.mean(0)
    # expand the quad until it covers the old footprint (its pinked teeth) completely
    ys, xs = np.nonzero(m); pts = np.c_[xs, ys].astype(np.float64)
    for k in np.arange(1.0, 1.08, 0.002):
        q = c + (Q - c) * k
        if (cv2.pointPolygonTest(q.astype(np.float32), (0, 0), False) or True) and all(cv2.pointPolygonTest(q.astype(np.float32), tuple(map(float, pt)), False) >= 0 for pt in pts[::37]): break
    K = 4
    mk = np.zeros((1350 * K, 1080 * K), np.uint8)
    cv2.fillPoly(mk, [np.int32(np.round(q * K * 16))], 255, cv2.LINE_AA, shift=4)
    A = cv2.resize(mk.astype(np.float32) / 255, (1080, 1350), interpolation=cv2.INTER_AREA)
    src = cv2.cvtColor(cv2.imread(str(ROOT / "source/jk_patch_post03.webp")), cv2.COLOR_BGR2RGB).astype(np.float32)
    h, w = src.shape[:2]; s = min(h, w); x0, y0 = (w - s) / 2, (h - s) / 2
    rect = np.float32([[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]])
    Hm = cv2.getPerspectiveTransform(rect, (q * 3).astype(np.float32))
    kk = np.sqrt(abs(np.linalg.det(Hm[:2, :2]))); src = cv2.GaussianBlur(src, (0, 0), 0.45 / kk) if kk < 1 else src
    tex = cv2.resize(cv2.warpPerspective(src, Hm, (3240, 4050), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), (1080, 1350), interpolation=cv2.INTER_AREA)
    # soft contact shadow: offset down-right (light from the top left), restrained
    sh = cv2.GaussianBlur(cv2.warpAffine(A, np.float32([[1, 0, 3], [0, 1, 5]]), (1080, 1350)), (0, 0), 5) * 0.35
    img = img * (1 - sh * (1 - A))[..., None]
    return tex * A[..., None] + img * (1 - A[..., None]), float(k)

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for i in (4, 5, 6): shutil.copyfile(SRC / f"0{i}.png", OUT / f"0{i}.png")
    for i, post in ((1, "POST_01"), (2, "POST_02"), (3, "POST_03")):
        fg = cv2.imread(str(ROOT / "work/thread" / f"{post}_fg.png"), 0) / 255.0
        pl, _ = RB.plate(post, fg < 0.7)
        img, A = post_0103_fixed(post, pl)
        if post == "POST_03":
            img, k = jk_patch(img); print("JK quad expansion", round(k, 3))
        cv2.imwrite(str(OUT / f"0{i}.png"), cv2.cvtColor(np.clip(img, 0, 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
        print(post, "ok")
    ims = [cv2.imread(str(OUT / f"0{i}.png")) for i in range(1, 7)]
    grid = np.vstack([np.hstack(ims[:3]), np.hstack(ims[3:])])
    cv2.imwrite(str(OUT / "preview_six_posts_full.png"), grid)
    cv2.imwrite(str(OUT / "preview_six_posts_small.jpg"), cv2.resize(grid, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
