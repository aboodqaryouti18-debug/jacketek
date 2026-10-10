"""JACKETEK website background identity -> Instagram posts 04-06.

Ports the website's own background layers (jacketportable src/styles/index.css
`.jk-atmos` + `--bg-studio` / `--bg-glow-layer`, colour worlds from
src/three/heroLayout.ts MOODS) to post size, then transfers them onto the
posts' BACKGROUND pixels only. Text, red words, dashed lines, photos, frames
and UI cards are never touched (same protection as tools/replace_photos/enhance.py).

  cream world ("finale" mood)       navy world ("navy" mood)
  base radial studio gradient       base radial studio gradient
  top-right second light            glow behind the subject (#A2BDC6, 0.4)
  window light + light shaft (UL)   textile grain (softer: x0.7)
  dusty-blue ambient (blurred)
  glow behind the subject (#FFFBF2)
  warm floor fall-off (no seam line)
  navy vignette (10%)
  textile grain (soft-light, site asset grain-soft-240.png)

The posts keep their own vertical hairlines (they play the role of the site's
pinstripe wall), their existing shadows, and their brand-colour mid tone: the
website layers are applied as a DELTA from the world's mid colour, so cream
stays cream and navy stays navy where the site's gradient passes through them.

Input : export/photo_update/POST_0X.png (jacket photos + shadows)
Output: export/website_background/POST_0X.png, grid + before/after
Usage : python3 tools/website_background.py [--site /home/user/jacketportable]
"""
import argparse, json, sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from background_treatment import background_weight, center_mask, SETTINGS  # noqa: E402

IN = ROOT / "export/photo_update"
OUT = ROOT / "export/website_background"
W = ROOT / "work/replace_photos"
STYLE = {"POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}
hexrgb = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)
P = dict(navy=hexrgb("#003049"), cream=hexrgb("#FCF0D6"), dusty=hexrgb("#669BBC"), oxblood=hexrgb("#780000"))
MOOD = {  # src/three/heroLayout.ts MOODS
    "beige": dict(center="#FFF8EA", mid="#FCF0D6", edge="#DCC8AE", glow="#FFFBF2", glowStrength=0.65, light=1, ambient=0.32),
    "navy": dict(center="#1F506B", mid="#003049", edge="#00131D", glow="#A2BDC6", glowStrength=0.4, light=0, ambient=0),
}
SITE_VIEW_W = 1080          # the posts are 1080 px wide on Instagram: site px -> post px
GRAIN_OPACITY = {1: 1.0, 0: 0.7}   # .jk-atmos__grain opacity: 0.7 + 0.3 * light


def ellipse_t(H, Wd, rx, ry, cx, cy):
    """CSS radial-gradient(ellipse rx ry at cx cy): distance in units of the ellipse radii."""
    yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
    return np.sqrt(((xx - cx * Wd) / (rx * Wd)) ** 2 + ((yy - cy * H) / (ry * H)) ** 2)


def stops(t, pts):
    """Piecewise-linear colour/alpha stops [(pos, value), ...] over t."""
    pos = np.array([p for p, _ in pts], np.float32); vals = np.array([v for _, v in pts], np.float32)
    tt = np.clip(t, pos[0], pos[-1])
    if vals.ndim == 1: return np.interp(tt, pos, vals)
    return np.stack([np.interp(tt, pos, vals[:, c]) for c in range(vals.shape[1])], -1)


def over(dst, rgb, a):
    a = np.clip(a, 0, 1)[..., None]
    return dst * (1 - a) + np.asarray(rgb, np.float32) * a


def render_world(style, H, Wd, subject, grain_tile):
    m = MOOD[style]; L = m["light"]; sx, sy = subject
    c0, c1, c2 = hexrgb(m["center"]), hexrgb(m["mid"]), hexrgb(m["edge"])
    k = Wd / SITE_VIEW_W
    # --bg-studio (bottom layer, then the top-right light above it)
    img = stops(ellipse_t(H, Wd, 0.60, 0.72, 0.5, 0.44), [(0, c0), (0.5, c1), (1, c2)])
    img = over(img, c0, stops(ellipse_t(H, Wd, 0.70, 0.55, 0.88, -0.06), [(0, 0.45), (0.70, 0)]))
    if L:
        win = hexrgb("#FFFCF4")
        img = over(img, win, stops(ellipse_t(H, Wd, 0.46, 0.64, 0.16, 0.08), [(0, 0.8), (0.72, 0)]))
        # linear-gradient(112deg ...): direction vector of the CSS angle, normalised gradient line
        a = np.radians(112); yy, xx = np.mgrid[0:H, 0:Wd].astype(np.float32)
        dx, dy = np.sin(a), -np.cos(a)
        glen = abs(Wd * np.sin(a)) + abs(H * np.cos(a))
        t = ((xx - Wd / 2) * dx + (yy - H / 2) * dy) / glen + 0.5
        img = over(img, win, stops(t, [(0.22, 0), (0.34, 0.22), (0.47, 0)]))
        # dusty-blue ambient behind the subject + a low second pool, blurred 24 site px
        amb = m["ambient"]
        aA = stops(ellipse_t(H, Wd, 0.26, 0.38, sx, sy), [(0, amb), (0.45, amb * 0.35), (0.75, 0)])
        aB = stops(ellipse_t(H, Wd, 0.26, 0.22, 0.18, 0.86), [(0, amb * 0.45), (0.70, 0)])
        ambient = np.zeros((H, Wd, 3), np.float32); alpha = np.zeros((H, Wd), np.float32)
        for aa in (aB, aA):
            ambient = over(ambient, P["dusty"], aa); alpha = alpha + aa * (1 - alpha)
        sig = 24 * k
        ambient = cv2.GaussianBlur(ambient, (0, 0), sig); alpha = cv2.GaussianBlur(alpha, (0, 0), sig)
        img = img * (1 - alpha[..., None]) + ambient
        # floor: warm oxblood fall-off below 84% (the 1px seam line is left out: it would cross the type)
        yy = np.mgrid[0:H, 0:Wd][0].astype(np.float32) / H
        # (the site hides the layer's hard top edge with its seam line; without the line it fades in)
        fl = np.clip(1 - (yy - 0.84) / (0.16 * 0.55), 0, 1) * 0.05 * np.clip((yy - 0.80) / 0.06, 0, 1) ** 2
        xm = stops(np.mgrid[0:H, 0:Wd][1].astype(np.float32) / Wd, [(0.08, 0), (0.34, 1), (0.84, 1), (0.98, 0)])
        img = over(img, P["oxblood"], fl * xm)
    # the light behind the jacket(s): --bg-glow-layer at the subject
    img = over(img, hexrgb(m["glow"]), stops(ellipse_t(H, Wd, 0.34, 0.42, sx, sy), [(0, m["glowStrength"]), (0.72, 0)]))
    if L:  # vignette
        img = over(img, P["navy"], stops(ellipse_t(H, Wd, 0.90, 0.88, 0.5, 0.42), [(0.58, 0), (1.0, 0.1)]))
    # textile grain: the site asset, tiled at 240 site px, soft-light blend at its own alpha
    g = cv2.resize(grain_tile, (max(8, round(240 * k)),) * 2, interpolation=cv2.INTER_AREA)
    reps = (H // g.shape[0] + 1, Wd // g.shape[1] + 1, 1)
    g = np.tile(g, reps)[:H, :Wd]
    gv, ga = g[..., 0] / 255, g[..., 3] / 255 * GRAIN_OPACITY[L]
    b = img / 255; s = gv[..., None]
    soft = np.where(s <= 0.5, b - (1 - 2 * s) * b * (1 - b), b + (2 * s - 1) * (np.where(b <= 0.25, ((16 * b - 12) * b + 4) * b, np.sqrt(b)) - b))
    img = (b * (1 - ga[..., None]) + soft * ga[..., None]) * 255
    return img, c1


def masks(post, rgb, bgw, L):
    """Protection masks exactly as in tools/replace_photos/enhance.py."""
    H, Wd = rgb.shape[:2]
    photos = np.zeros((H, Wd), np.uint8)
    for p, s, e, r, n in L["SLOTS"]:
        if p == post: photos |= (cv2.imread(str(W / e["slot_mask"]), 0) > 0)
    if post == "POST_06":
        e = [x for x in L["POST_06"] if x["render"] == "chest"][0]
        q = np.zeros((H, Wd), np.uint8); cv2.fillPoly(q, [np.int32(np.round(e["corners"]))], 1); photos |= q
    if post == "POST_05": photos |= (cv2.imread(str(W / "POST_05_cards.png"), 0) > 0)
    frame = (rgb.min(2) > 226) & (rgb[..., 2] > 228)
    obj = cv2.morphologyEx((frame | (photos > 0)).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(obj)
    prints = np.zeros((H, Wd), np.float32)
    for i in range(1, n):
        comp = lab == i
        if st[i, cv2.CC_STAT_AREA] > 12000 and (photos[comp] > 0).sum() > 500: prints[comp] = 1
    prints = cv2.GaussianBlur(prints, (0, 0), 0.7)
    ref = {"beige": (253, 239, 212), "navy": (0, 48, 72)}[STYLE[post]]
    a = rgb.astype(np.float32); c1, c2 = a[..., 0] - a[..., 2], a[..., 1] - a[..., 2]
    chroma = np.sqrt((c1 - (ref[0] - ref[2])) ** 2 + (c2 - (ref[1] - ref[2])) ** 2)
    lumd = np.abs(a.mean(2) - sum(ref) / 3)
    # coverage of type/graphics per pixel: 1 inside letters (left exactly as they are),
    # fractional on anti-aliased edges (blended), 0 on plain background
    sm = lambda x, a0, a1: np.clip((x - a0) / (a1 - a0), 0, 1)
    cov = np.maximum(sm(chroma, 6, 36), sm(lumd, 14, 100))
    cov[cov > 0.9] = 1
    cov = cov * (prints < 0.5)
    return np.clip(1 - prints, 0, 1) * (1 - cov), prints


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--site", default="/home/user/jacketportable"); ap.add_argument("--strength", type=float, default=1.0)
    a = ap.parse_args()
    grain = cv2.imread(str(Path(a.site) / "public/assets/texture/grain-soft-240.png"), cv2.IMREAD_UNCHANGED)
    grain = cv2.cvtColor(grain, cv2.COLOR_BGRA2RGBA).astype(np.float32)
    L = json.loads((W / "locate.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True); outs, ins, report = [], [], {}
    for post in ("POST_04", "POST_05", "POST_06"):
        bgr = cv2.imread(str(IN / f"{post}.png")); rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB); H, Wd = rgb.shape[:2]
        style = STYLE[post]
        bgw = background_weight(rgb, style)
        w, prints = masks(post, rgb, bgw, L)
        # subject = centroid of the jacket prints (the site centres its lights on the jacket)
        ys, xs = np.nonzero(prints > 0.5); subject = (xs.mean() / Wd, ys.mean() / H)
        world, mid = render_world(style, H, Wd, subject, grain)
        # undo the earlier posts-only centre depth (beige darkened its centre; the site lights it instead)
        dep = SETTINGS[style]["depth"] * center_mask(Wd, H)
        base = rgb.astype(np.float32) / (1 + dep * w)[..., None]
        delta = (world - mid) * a.strength
        out = np.clip(base + delta * w[..., None], 0, 255)
        out = np.where((w > 0)[..., None], out, rgb.astype(np.float32)).round().astype(np.uint8)
        cv2.imwrite(str(OUT / f"{post}.png"), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(W.parent / "website_background" / f"{post}_world.png"), cv2.cvtColor(np.clip(world, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))
        prot = w <= 1e-6
        report[post] = dict(subject=[round(subject[0], 3), round(subject[1], 3)],
                            protected_px=int(prot.sum()),
                            protected_px_changed=int((np.abs(out.astype(int) - rgb.astype(int)).max(2)[prot] > 0).sum()))
        outs.append(cv2.cvtColor(out, cv2.COLOR_RGB2BGR)); ins.append(bgr)
    grid = np.hstack(outs); cv2.imwrite(str(OUT / "grid_preview.png"), grid)
    cv2.imwrite(str(OUT / "grid_before_after.jpg"), np.vstack([np.hstack(ins), np.full((20, grid.shape[1], 3), 255, np.uint8), grid]), [cv2.IMWRITE_JPEG_QUALITY, 92])
    (OUT / "report.json").write_text(json.dumps(report, indent=1)); print(json.dumps(report))


if __name__ == "__main__":
    main()
