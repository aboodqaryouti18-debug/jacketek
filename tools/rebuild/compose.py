"""Rebuild Instagram posts 04-06 at 1080 x 1350 from their separate elements.

Nothing here resamples a flattened post. Every layer is rebuilt at the final size
from its source, in the approved layout (measured on the original grid, panel px):

  background   flat brand colour x the design's print shadows (shadow_fit.json)
               x the hairlines (tools/background_treatment.py) x the print shadows
               of tools/replace_photos/enhance.py + the website world
               (tools/website_background.py), all evaluated at 1080 x 1350
  dashes       vector arcs / lines (dash_model.json), under the prints
  prints       white frames (frames.json) + the 2000 px jacket photos
               (source/new_photos, transforms from work/replace_photos/locate.json),
               the JK chest render, and the two configurator cards re-captured
               from the live site at 3x (work/rebuild/site)
  type         DARK ExtraBold, set by the browser at 600 px (work/rebuild/text),
               placed by fit.json; the three red words are the website 3D
               embroidery renders (work/website_embroidery/render, 6x)
  patches      the baked embroidered patches (work/patches/baked, ~4x)

Grid panel (3:4) -> 4:5 post: Instagram's profile grid shows the centre 3:4 of
each post, so panel px -> post px is x' = OX + S x, y' = S y with S = 1350/888.
The 33 px side strips outside the panel are background (lines and dashed
guides continue into them).

Usage: python3 tools/rebuild/compose.py [POST_04 POST_05 POST_06]
"""
import json, sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/rebuild"))
import background_treatment as bt  # noqa: E402
import website_background as wb  # noqa: E402
from text_runs import RUNS, NAVY, CREAM, RED  # noqa: E402

W_OUT, H_OUT = 1080, 1350
SS = 2                                   # vector / photo layers are rendered at 2x, then area-averaged
S = H_OUT / 888.0
PANEL_W = {"POST_04": 667, "POST_05": 666, "POST_06": 667}
STYLE = {"POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}
FLAT = {"beige": np.array([253.1, 239.3, 212.1]), "navy": np.array([0.4, 48.0, 72.3])}
FRAME_WHITE = np.array([255, 253, 245], np.float64)
SUBJECT = {"POST_04": (0.533, 0.512), "POST_05": (0.521, 0.616), "POST_06": (0.46, 0.386)}
Z = {"POST_04": ["big", "small"], "POST_05": ["front", "card1", "card2"], "POST_06": ["number", "chest", "collar"]}
WR = ROOT / "work/rebuild"
J = lambda p: json.loads((ROOT / p).read_text())


def ox(post):
    return (W_OUT - PANEL_W[post] * S) / 2


def A(post, ss=1):
    """panel px -> output px (x ss)"""
    return np.array([[S * ss, 0, ox(post) * ss], [0, S * ss, 0], [0, 0, 1.0]])


def to_out(M2x3, post, ss):
    """compose a (src -> panel) affine with panel -> output (x ss)"""
    M = np.vstack([np.asarray(M2x3, np.float64), [0, 0, 1]])
    return (A(post, ss) @ M)[:2]


def down(img):
    """SS canvas -> output (area average)"""
    return cv2.resize(img, (W_OUT, H_OUT), interpolation=cv2.INTER_AREA)


def poly_mask(pts_panel, post, ss=SS):
    """anti-aliased quad mask at output resolution"""
    q = (np.c_[np.asarray(pts_panel, float), np.ones(len(pts_panel))] @ A(post, ss).T)[:, :2]
    m = np.zeros((H_OUT * ss, W_OUT * ss), np.uint8)
    cv2.fillPoly(m, [np.int32(np.round(q * 16))], 255, cv2.LINE_AA, shift=4)
    return down(m.astype(np.float32) / 255) if ss > 1 else m.astype(np.float32) / 255


# ---------------------------------------------------------------- background
def panel_coords(post):
    yy, xx = np.mgrid[0:H_OUT, 0:W_OUT].astype(np.float32)
    return (xx + 0.5 - ox(post)) / S - 0.5, (yy + 0.5) / S - 0.5       # panel px at pixel centres


def lines_gain(post):
    """tools/background_treatment.py line layer, in panel coordinates (the depth term
    was undone by tools/website_background.py, so it is left out)."""
    style = STYLE[post]; cfg = bt.SETTINGS[style]; w, h = PANEL_W[post], 888
    xp, yp = panel_coords(post)
    spacing = w / bt.LINES_PER_WIDTH
    s = w / 709.0
    # the posts sampled these profiles once per panel pixel; here they are integrated
    # over each output pixel (3x3 subsamples) so the line keeps its weight
    dark = np.zeros_like(xp); light = np.zeros_like(xp)
    for o in (-1 / 3, 0, 1 / 3):
        dd = np.abs(((xp + 0.5 + o / S - spacing / 2) % spacing) - spacing / 2)
        dark += np.exp(-(dd / (0.65 * s)) ** 2) / 3
        light += np.exp(-((dd - 2.2 * s) / (1.1 * s)) ** 2) * (dd > 0.8 * s) / 3
    v = (yp + 0.5) / h
    vfade = 0.55 + 0.45 * bt.smoothstep(0.0, 0.25, v) * bt.smoothstep(0.0, 0.25, 1 - v)
    u = (xp + 0.5) / w * 2 - 1; vv = (yp + 0.5) / h * 2 - 1
    g = np.exp(-((u / 0.66) ** 2 + (vv / 0.64) ** 2))
    win = bt.smoothstep(-0.1, 0.9, 1 - np.abs(u)) * bt.smoothstep(-0.1, 0.9, 1 - np.abs(vv))
    m = g * win
    m = m / m.max()
    amt = bt.line_amount(m)
    return (1 - cfg["line_dark"] * dark * vfade * amt) * (1 + cfg["line_light"] * light * vfade * amt)


def blur_shift(m, dx, dy, sig):
    t = cv2.warpAffine(m, np.float32([[1, 0, dx], [0, 1, dy]]), m.shape[::-1])
    return cv2.GaussianBlur(t, (0, 0), max(sig, 0.3))


def design_shadow(P, style):
    p = J("work/rebuild/shadow_fit.json")[style]
    return (1 - p["k1"] * blur_shift(P, p["dx1"] * S, p["dy1"] * S, p["s1"] * S)) * \
           (1 - p["k2"] * blur_shift(P, p["dx2"] * S, p["dy2"] * S, p["s2"] * S))


def enhance_shadow(P, post, sweep_on=True):
    """tools/replace_photos/enhance.py (drop + contact shadow, gentle sweep), in panel units."""
    cfg = {"beige": dict(drop=0.20, contact=0.22, grad=0.035), "navy": dict(drop=0.38, contact=0.30, grad=0.05)}[STYLE[post]]
    L = np.array([0.6, 1.0]); L = L / np.linalg.norm(L)
    drop = blur_shift(P, 11 * L[0] * S, 11 * L[1] * S, 11 * S)
    contact = blur_shift(P, 2.0 * L[0] * S, 2.0 * L[1] * S, 2.2 * S)
    xp, yp = panel_coords(post)
    t = ((xp / PANEL_W[post]) * L[0] + (yp / 888) * L[1]) / L.sum()
    sweep = 1 + cfg["grad"] * (0.5 - t) * 2 * 0.5 if sweep_on else 1
    return (1 - cfg["drop"] * drop) * (1 - cfg["contact"] * contact) * sweep


def world(post, grain_tile):
    """tools/website_background.render_world, evaluated in panel coordinates on the 4:5 canvas."""
    style = STYLE[post]; m = wb.MOOD[style]; Lt = m["light"]; sx, sy = SUBJECT[post]
    c0, c1, c2 = wb.hexrgb(m["center"]), wb.hexrgb(m["mid"]), wb.hexrgb(m["edge"])
    Wp = PANEL_W[post] * S; H = H_OUT
    k = Wp / wb.SITE_VIEW_W
    xx, yy = np.mgrid[0:H, 0:W_OUT][::-1]
    xx = (xx.astype(np.float32) - ox(post)); yy = yy.astype(np.float32)
    def ell(rx, ry, cx, cy):
        return np.sqrt(((xx - cx * Wp) / (rx * Wp)) ** 2 + ((yy - cy * H) / (ry * H)) ** 2)
    img = wb.stops(ell(0.60, 0.72, 0.5, 0.44), [(0, c0), (0.5, c1), (1, c2)])
    img = wb.over(img, c0, wb.stops(ell(0.70, 0.55, 0.88, -0.06), [(0, 0.45), (0.70, 0)]))
    if Lt:
        win = wb.hexrgb("#FFFCF4")
        img = wb.over(img, win, wb.stops(ell(0.46, 0.64, 0.16, 0.08), [(0, 0.8), (0.72, 0)]))
        a = np.radians(112); dx, dy = np.sin(a), -np.cos(a)
        glen = abs(Wp * np.sin(a)) + abs(H * np.cos(a))
        t = ((xx - Wp / 2) * dx + (yy - H / 2) * dy) / glen + 0.5
        img = wb.over(img, win, wb.stops(t, [(0.22, 0), (0.34, 0.22), (0.47, 0)]))
        amb = m["ambient"]
        aA = wb.stops(ell(0.26, 0.38, sx, sy), [(0, amb), (0.45, amb * 0.35), (0.75, 0)])
        aB = wb.stops(ell(0.26, 0.22, 0.18, 0.86), [(0, amb * 0.45), (0.70, 0)])
        ambient = np.zeros((H, W_OUT, 3), np.float32); alpha = np.zeros((H, W_OUT), np.float32)
        for aa in (aB, aA):
            ambient = wb.over(ambient, wb.P["dusty"], aa); alpha = alpha + aa * (1 - alpha)
        sig = 24 * k
        ambient = cv2.GaussianBlur(ambient, (0, 0), sig); alpha = cv2.GaussianBlur(alpha, (0, 0), sig)
        img = img * (1 - alpha[..., None]) + ambient
        yr = yy / H
        fl = np.clip(1 - (yr - 0.84) / (0.16 * 0.55), 0, 1) * 0.05 * np.clip((yr - 0.80) / 0.06, 0, 1) ** 2
        xm = wb.stops(xx / Wp, [(0.08, 0), (0.34, 1), (0.84, 1), (0.98, 0)])
        img = wb.over(img, wb.P["oxblood"], fl * xm)
    img = wb.over(img, wb.hexrgb(m["glow"]), wb.stops(ell(0.34, 0.42, sx, sy), [(0, m["glowStrength"]), (0.72, 0)]))
    if Lt:
        img = wb.over(img, wb.P["navy"], wb.stops(ell(0.90, 0.88, 0.5, 0.42), [(0.58, 0), (1.0, 0.1)]))
    base = img.copy()
    g = cv2.resize(grain_tile, (max(8, round(240 * k)),) * 2, interpolation=cv2.INTER_AREA)
    reps = (H // g.shape[0] + 1, W_OUT // g.shape[1] + 1, 1)
    g = np.tile(g, reps)[:H, :W_OUT]
    gv, ga = g[..., 0] / 255, g[..., 3] / 255 * wb.GRAIN_OPACITY[Lt]
    b = img / 255; s = gv[..., None]
    soft = np.where(s <= 0.5, b - (1 - 2 * s) * b * (1 - b), b + (2 * s - 1) * (np.where(b <= 0.25, ((16 * b - 12) * b + 4) * b, np.sqrt(b)) - b))
    img = (b * (1 - ga[..., None]) + soft * ga[..., None]) * 255
    return img, c1


def prints_union(post):
    F = {f["id"]: f for f in J("work/rebuild/frames.json")[post]}
    P = np.zeros((H_OUT, W_OUT), np.float32)
    for fid in Z[post]:
        m = poly_mask(F[fid]["outer"], post); P = P + m * (1 - P)
    return P


def background(post, grain_tile):
    style = STYLE[post]
    P = prints_union(post)
    bg = np.ones((H_OUT, W_OUT, 3), np.float32) * FLAT[style].astype(np.float32)
    bg *= (design_shadow(P, style) * lines_gain(post) * enhance_shadow(P, post))[..., None]
    w, mid = world(post, grain_tile)
    return np.clip(bg + (w - mid), 0, 255), P


# The background of the reference grid (posts 01-03): see tools/rebuild/ref_background_fit.py
BG_MODE = "website"   # "website" (approved rebuild) or "reference" (posts 01-03 finish)
REF_GRAIN = 0.45      # the reference's background is near-flat: the site grain at under half strength


def reference_light(post):
    """the reference beige's light (elliptical + floor fall-off) in panel coordinates; navy: flat"""
    R = J("work/rebuild/ref_background.json")
    if STYLE[post] == "navy":
        return np.ones((H_OUT, W_OUT), np.float32), np.array(R["navy"]["colour"], np.float32)
    q = R["beige"]["params"]
    xp, yp = panel_coords(post)
    u = (xp + 0.5) / PANEL_W[post]; v = (yp + 0.5) / 888
    f = np.clip((v - q["floor_from"]) / (1 - q["floor_from"]), 0, 1)
    g = (1 - q["a_u"] * ((u - 0.5) / 0.5) ** 2 - q["a_v"] * ((v - q["v_centre"]) / 0.5) ** 2) * (1 - q["floor"] * f * f)
    return g.astype(np.float32), np.array(R["beige"]["peak_colour"], np.float32)


def grain_only(img, grain_tile, strength):
    """the site's textile grain (soft-light), on its own, at a given strength"""
    k = PANEL_W["POST_04"] * S / wb.SITE_VIEW_W
    g = cv2.resize(grain_tile, (max(8, round(240 * k)),) * 2, interpolation=cv2.INTER_AREA)
    g = np.tile(g, (H_OUT // g.shape[0] + 1, W_OUT // g.shape[1] + 1, 1))[:H_OUT, :W_OUT]
    gv, ga = g[..., 0] / 255, g[..., 3] / 255 * strength
    b = img / 255; s_ = gv[..., None]
    soft = np.where(s_ <= 0.5, b - (1 - 2 * s_) * b * (1 - b), b + (2 * s_ - 1) * (np.where(b <= 0.25, ((16 * b - 12) * b + 4) * b, np.sqrt(b)) - b))
    return (b * (1 - ga[..., None]) + soft * ga[..., None]) * 255


def background_reference(post, grain_tile):
    """posts 01-03's background on 04-06, each post keeping its own colour world:
    the reference's beige / navy and its light, the faint hairlines, the print shadows,
    a near-flat grain. (The website world's glow, window light and vignette are left out.)"""
    style = STYLE[post]
    P = prints_union(post)
    gain, colour = reference_light(post)
    bg = np.ones((H_OUT, W_OUT, 3), np.float32) * colour
    bg *= (gain * design_shadow(P, style) * lines_gain(post) * enhance_shadow(P, post, sweep_on=False))[..., None]
    return np.clip(grain_only(bg, grain_tile, REF_GRAIN), 0, 255), P


# ---------------------------------------------------------------- layers (premultiplied RGBA, output res)
def over(dst, rgb_pm, a):
    """dst (H,W,3) <- premultiplied layer"""
    return rgb_pm + dst * (1 - a[..., None])


def dashes_layer(post):
    """vector dashes: 9.1 x 1.8 panel px rectangles along each fitted arc / line"""
    D = J("work/rebuild/dash_model.json"); L, Wd = D["dash"]["length"], D["dash"]["width"]
    col = np.array(NAVY if STYLE[post] == "beige" else CREAM, np.float64)
    m = np.zeros((H_OUT * SS, W_OUT * SS), np.uint8)
    Aq = A(post, SS)
    x_lo, x_hi = -ox(post) / S - 5, PANEL_W[post] + ox(post) / S + 5        # post edges in panel px
    def dash(c, d):
        n = np.array([-d[1], d[0]])
        q = np.array([c + d * L / 2 + n * Wd / 2, c - d * L / 2 + n * Wd / 2, c - d * L / 2 - n * Wd / 2, c + d * L / 2 - n * Wd / 2])
        q = (np.c_[q, np.ones(4)] @ Aq.T)[:, :2]
        cv2.fillPoly(m, [np.int32(np.round(q * 16))], 255, cv2.LINE_AA, shift=4)
    for ln in D.get(post, []):
        per = ln["period"]
        if ln["kind"] == "arc":
            cx, cy, r, th0, sg = ln["cx"], ln["cy"], ln["r"], ln["th0"], ln["sign"]
            s_lo = ln["s_first"] - (2000 if ln["extend_start"] else 0)
            s_hi = ln["s_last"] + (2000 if ln["extend_end"] else 0)
            k0 = int(np.floor((s_lo - ln["s0"]) / per)); k1 = int(np.ceil((s_hi - ln["s0"]) / per))
            for k in range(k0, k1 + 1):
                s = ln["s0"] + k * per
                if s < s_lo - 1e-6 or s > s_hi + 1e-6: continue
                if any(a <= k <= b for a, b in ln.get("hidden_k", [])): continue
                th = th0 + sg * s / r
                c = np.array([cx + r * np.cos(th), cy + r * np.sin(th)])
                if not (x_lo <= c[0] <= x_hi and -10 <= c[1] <= 898): continue
                d = sg * np.array([-np.sin(th), np.cos(th)])
                dash(c, d)
        else:   # straight: dashes through `anchor` (a measured dash centre), every period
            a = np.radians(ln["angle"]); d = np.array([np.cos(a), np.sin(a)]); c0 = np.array(ln["anchor"], float)
            if post == "POST_05" and ln["id"] == "to_06": c0 = c0 - [PANEL_W["POST_05"], 0]   # anchor measured in 06's panel
            if post == "POST_04" and ln["id"] == "to_05": c0 = c0 - [667, 0]
            for k in range(-80, 81):
                c = c0 + d * per * k
                if not (x_lo <= c[0] <= x_hi): continue
                if ln.get("from_x") is not None and c[0] < ln["from_x"]: continue
                if ln.get("to_x") is not None and c[0] > ln["to_x"]: continue
                dash(c, d)
    a = down(m.astype(np.float32) / 255)
    return col[None, None] * a[..., None], a


def warp_photo(src, M_out_ss):
    """area-correct resample of a large source photo onto the SS canvas"""
    s = np.hypot(M_out_ss[0, 0], M_out_ss[1, 0])
    if s < 1: src = cv2.GaussianBlur(src, (0, 0), 0.45 / s)
    return cv2.warpAffine(src, M_out_ss, (W_OUT * SS, H_OUT * SS), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def photo_content(post, fid):
    """the photo inside a print window: (rgb at output res, from the highest-res source)"""
    L = J("work/replace_photos/locate.json")
    if post == "POST_06" and fid == "chest":
        e = [x for x in L["POST_06"] if x["render"] == "chest"][0]
        src = cv2.cvtColor(cv2.imread(str(ROOT / "source/renders/04_chest_letters.png")), cv2.COLOR_BGR2RGB).astype(np.float32)
        M = np.array(e["M"], np.float64)
    else:
        slot = {"big": "big", "small": "small", "front": "front", "number": "number", "collar": "collar"}[fid]
        p, sl, e, rf, nf = [s for s in L["SLOTS"] if s[0] == post and s[1] == slot][0]
        src = cv2.cvtColor(cv2.imread(str(ROOT / "source/new_photos" / nf)), cv2.COLOR_BGR2RGB).astype(np.float32)
        nh, nw = src.shape[:2]; rw, rh = e["size"]
        M = (np.vstack([np.array(e["M"], np.float64), [0, 0, 1]]) @ np.diag([rw / nw, rh / nh, 1]))[:2]
    return down(warp_photo(src, to_out(M, post, SS)))


CARD_BLANK_FROM = {"card1": 1790}   # capture px (3x)


def card_content(post, fid):
    """configurator card: the live-site capture, mapped onto the card window (homography fit)."""
    H_ = np.array(J("work/rebuild/cards.json")[fid]["H_out"], np.float64)
    src = cv2.cvtColor(cv2.imread(str(WR / "site" / J("work/rebuild/cards.json")[fid]["file"])), cv2.COLOR_BGR2RGB).astype(np.float32)
    # below what the card shows, today's site has more panel (card 1: the material
    # section): the original card is blank cream there, so the capture is too
    cut = CARD_BLANK_FROM.get(fid)
    if cut: src[cut:] = src[cut - 6:cut - 5]
    Hss = np.diag([SS, SS, 1]) @ H_
    s = np.sqrt(abs(np.linalg.det(Hss[:2, :2])))
    if s < 1: src = cv2.GaussianBlur(src, (0, 0), 0.45 / s)
    big = cv2.warpPerspective(src, Hss, (W_OUT * SS, H_OUT * SS), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return down(big)


def prints_layers(post, img):
    """frames + their contents, bottom to top; each print also shades the prints under it"""
    F = {f["id"]: f for f in J("work/rebuild/frames.json")[post]}
    below = np.zeros((H_OUT, W_OUT), np.float32)
    for fid in Z[post]:
        f = F[fid]
        outer = poly_mask(f["outer"], post); win = poly_mask(f["window"], post)
        if below.max() > 0:
            # this print's shadow on the prints already placed under it (the design shadow model)
            sh = design_shadow(outer, STYLE[post])
            img = img * (1 - (1 - sh) * below)[..., None]
        content = card_content(post, fid) if f["kind"] == "card" else photo_content(post, fid)
        frame = np.ones_like(img) * FRAME_WHITE
        layer = frame * (1 - win[..., None]) + content * win[..., None]
        img = img * (1 - outer[..., None]) + layer * outer[..., None]
        below = below + outer * (1 - below)
    return img


def text_layers(post, img):
    """type: DARK masks (600 px, browser-shaped) placed by fit.json; red words = embroidery renders"""
    fit = J("work/rebuild/text/fit.json")
    col = {"navy": np.array(NAVY, float), "cream": np.array(CREAM, float), "red": np.array(RED, float)}
    for r in RUNS[post]:
        if r.get("embroidered"):
            img = red_word(post, img); continue
        f = fit[r["id"]]
        m = cv2.imread(str(WR / "text" / f"{r['id']}_600.png"), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255
        M = to_out([[f["s"], 0, f["tx"]], [0, f["s"], f["ty"]]], post, SS)
        a = down(cv2.warpAffine(cv2.GaussianBlur(m, (0, 0), max(0.3, 0.45 / np.hypot(M[0, 0], M[1, 0]))), M, (W_OUT * SS, H_OUT * SS), flags=cv2.INTER_LINEAR))
        a *= r.get("opacity", 1.0)
        img = over(img, col[r["colour"]][None, None] * a[..., None], a)
    return img


def red_word(post, img):
    """the website 3D embroidery renders (tools/website_embroidery, K=6 x panel), dyed crimson"""
    sys.path.insert(0, str(ROOT / "tools/website_embroidery"))
    import run_pipeline as rp
    fits = {r["name"]: r for r in json.loads((rp.W / "dark_fit.json").read_text())}
    meta = json.loads((rp.W / "masks" / "meta.json").read_text())
    f, m = fits[post], meta[post]
    k = 600 / m["px"]
    M = [[f["sx"] * k, 0, f["tx"] + f["sx"] * (40 - m["pad"] * k)], [0, f["sy"] * k, f["ty"] + f["sy"] * (40 - m["pad"] * k)]]
    thread = rp.read_rgba(rp.W / "render" / post / "render_thread.png")
    shadow = rp.read_rgba(rp.W / "render" / post / "render_shadow.png")
    dyed, _ = rp.dye(thread)
    Mo = to_out(M, post, SS)
    wp = lambda x: down(cv2.warpAffine(x.astype(np.float32), Mo, (W_OUT * SS, H_OUT * SS), flags=cv2.INTER_LINEAR))
    t_a = wp(thread[..., 3]); t_rgb = wp(dyed * thread[..., 3:4]) * 255; s_a = wp(shadow[..., 3])
    img = img * (1 - s_a[..., None])
    return over(img, t_rgb, t_a)


# Placements that differ from the approved ones in tools/patches/composite.py.
# POST_04: the car patch moved off the sleeve onto the big print's top-left corner,
# a standalone patch overlapping the frame edge like the clock on its bottom-left
# corner (the clock stays exactly as approved).
PATCH_PLACE = {
    "POST_04": [("whocares", (114, 607), 132, 9.0, "standalone"),
                ("porsche", (72, 228), 100, -6.0, "standalone")],
}


def patches_layer(post, img, light_img=None):
    """the approved patch placements (tools/patches/composite.py, panel px), rendered from the
    baked embroidered patches (work/patches/baked, ~820 px) straight to the output size"""
    sys.path.insert(0, str(ROOT / "tools/patches"))
    import composite as pc
    LUMW = np.float32([0.2126, 0.7152, 0.0722])
    for n, c, D, rot, kind in PATCH_PLACE.get(post, pc.PLACE[post]):
        t, sh = pc.load(n)
        M = to_out(pc.matrix(t[..., 3], c, D, rot), post, SS)
        remap = None
        if kind == "sewn":
            sl = pc.SLEEVE[n]
            Hs, Ws = H_OUT * SS, W_OUT * SS
            xx, yy = np.meshgrid(np.arange(Ws, dtype=np.float32), np.arange(Hs, dtype=np.float32))
            cx = (ox(post) + sl["cx"] * S) * SS; R = sl["half_width"] * 1.15 * S * SS
            d = np.clip((xx - cx) / R, -0.999, 0.999)
            remap = ((cx + R * np.arcsin(d)).astype(np.float32), yy)
        def wp(x, Mx=M):
            big = cv2.warpAffine(x, Mx, (W_OUT * SS, H_OUT * SS), flags=cv2.INTER_LINEAR, borderValue=0)
            if remap is not None: big = cv2.remap(big, remap[0], remap[1], cv2.INTER_LINEAR, borderValue=0)
            return down(big)
        a = wp(t[..., 3]); col = wp(t[..., :3] * t[..., 3:4]) * 255; shw = wp(sh)
        lum = (img if light_img is None else light_img) @ LUMW
        if kind == "standalone":
            lf = pc.LIFT[STYLE[post]]
            Mo = to_out(pc.matrix(t[..., 3], (c[0] + lf["off"][0], c[1] + lf["off"][1]), D, rot), post, SS)
            lift = cv2.GaussianBlur(wp(t[..., 3], Mo), (0, 0), lf["sigma"] * S) * lf["k"]
            light = cv2.GaussianBlur(lum, (0, 0), 30 * S)
            refl = np.median(light[a > 0.5])
            tone = np.clip(1 + (light / max(refl, 1e-3) - 1) * 0.35, 0.92, 1.05)
        else:
            lift = np.zeros_like(a)
            fab = cv2.GaussianBlur(lum, (0, 0), 3.0 * S)
            ring = (cv2.dilate((a > 0.02).astype(np.uint8), np.ones((13, 13))) > 0) & (a < 0.02)
            refl = np.median(fab[ring])
            tone = np.clip(fab / refl, 0.75, 1.08) ** 0.9
        dark = 1 - np.clip(lift + shw * pc.CONTACT_K, 0, 0.85)
        img = img * dark[..., None]
        img = col * tone[..., None] + img * (1 - a[..., None])
    return img


def build(post):
    grain = cv2.cvtColor(cv2.imread("/home/user/jacketportable/public/assets/texture/grain-soft-240.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32)
    img, P = (background_reference if BG_MODE == "reference" else background)(post, grain)
    d_rgb, d_a = dashes_layer(post)
    img = over(img, d_rgb, d_a)
    img = prints_layers(post, img)
    img = text_layers(post, img)
    light_img = None
    if BG_MODE == "reference":
        # the patches keep their approved look exactly: their tone is read from the
        # approved (website-background) composite, not from the new background
        w, _ = background(post, grain)
        light_img = text_layers(post, prints_layers(post, over(w, d_rgb, d_a)))
    img = patches_layer(post, img, light_img)
    return img


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--reference-bg" in args:
        BG_MODE = "reference"; args.remove("--reference-bg")
    posts = args or ["POST_04", "POST_05", "POST_06"]
    stage = WR / ("stage_reference_bg" if BG_MODE == "reference" else "stage")
    stage.mkdir(parents=True, exist_ok=True)
    for post in posts:
        img = build(post)
        cv2.imwrite(str(stage / f"{post}.png"), cv2.cvtColor(np.clip(img, 0, 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
        print(post, "ok")
