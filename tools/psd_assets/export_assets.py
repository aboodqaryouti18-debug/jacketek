"""Photoshop asset export: every approved post (export/quality_fixed/0X.png) taken apart into
separate, aligned layers on a 3240 x 4050 canvas (3x the 1080 x 1350 post).

Every layer is a full-canvas PNG (origin 0,0, same size), straight (not premultiplied) RGBA.
Posts 04-06 are re-rendered layer by layer from their sources at 3x with the approved
pipeline (tools/rebuild/compose.py + tools/newbg/replace_photos_l.py); posts 01-03 are split
from their only source (the 667 px grid) at 3x, with the JK patch from its 2000 px photo.
The background of all six is tools/psd_assets/background_vector.py (vector dots + thread).

-> export/photoshop_assets/0X/  (layers, text.svg, layout.json, preview.png, final_1080.png)
Usage: python3 tools/psd_assets/export_assets.py [01 02 ...]   (run from tools/newbg)"""
import json, sys, shutil
from pathlib import Path
import cv2, numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/newbg")); sys.path.insert(0, str(ROOT / "tools/quality"))
import replace_photos_l as RPL           # installs the burgundy photos into compose
RB = RPL.RB; C = RB.C; P3 = RB.P3
sys.path.insert(0, str(ROOT / "tools/patches")); import composite as pc

K = 3
C.W_OUT, C.H_OUT = 1080 * K, 1350 * K
C.S = C.H_OUT / 888.0
C.SS = 1
W, H = C.W_OUT, C.H_OUT
OUT = ROOT / "export/photoshop_assets"
POSTS = {"01": "POST_01", "02": "POST_02", "03": "POST_03", "04": "POST_04", "05": "POST_05", "06": "POST_06"}
LUM = np.float32([0.299, 0.587, 0.114])


# ------------------------------------------------------------------ layer bookkeeping
class Post:
    def __init__(self, num):
        self.num, self.post = num, POSTS[num]
        self.dir = OUT / num; self.dir.mkdir(parents=True, exist_ok=True)
        for f in self.dir.glob("*"): f.unlink()
        self.layers = []
        self.comp = None

    def add(self, name, rgb, alpha, kind, note="", source="", blend="normal"):
        """rgb: (H,W,3) or colour triple; alpha (H,W) 0..1. Written as full-canvas RGBA."""
        a = np.clip(alpha, 0, 1).astype(np.float32)
        if a.max() < 1 / 255:
            return
        rgb = np.broadcast_to(np.asarray(rgb, np.float32), (H, W, 3)) if np.ndim(rgb) == 1 else rgb
        a8 = (a * 255).round().astype(np.uint8)
        rgba = np.dstack([np.clip(rgb, 0, 255).round().astype(np.uint8), a8])
        rgba[a8 == 0, :3] = 0
        fn = f"{len(self.layers):02d}_{name}.png"
        cv2.imwrite(str(self.dir / fn), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA), [cv2.IMWRITE_PNG_COMPRESSION, 6])
        ys, xs = np.nonzero(a8)
        a = a8.astype(np.float32)[..., None] / 255
        rgbq = rgba[..., :3].astype(np.float32)
        if self.comp is None:
            self.comp = rgbq * a
        else:
            self.comp = rgbq * a + self.comp * (1 - a)
        self.layers.append(dict(order=len(self.layers), file=fn, name=name, type=kind, blend=blend, opacity=100,
                                x=0, y=0, width=W, height=H,
                                content_bbox=dict(x=int(xs.min()), y=int(ys.min()), width=int(xs.max() - xs.min() + 1), height=int(ys.max() - ys.min() + 1)),
                                rotation_deg=0, scale=1.0, source=source, note=note))

    def finish(self, svg_files, approved, extra):
        pv = np.clip(self.comp, 0, 255).round().astype(np.uint8)
        cv2.imwrite(str(self.dir / "preview_3240x4050.png"), cv2.cvtColor(pv, cv2.COLOR_RGB2BGR))
        small = cv2.resize(self.comp, (1080, 1350), interpolation=cv2.INTER_AREA)
        s8 = np.clip(small, 0, 255).round().astype(np.uint8)
        cv2.imwrite(str(self.dir / "final_1080x1350.png"), cv2.cvtColor(s8, cv2.COLOR_RGB2BGR))
        d = np.abs(s8.astype(int) - approved.astype(int)).max(2)
        check = dict(mean_abs_diff=round(float(d.mean()), 2), p99=round(float(np.percentile(d, 99)), 1),
                     share_px_diff_over_16=round(float((d > 16).mean()), 4))
        side = np.hstack([approved, np.full((1350, 16, 3), 255, np.uint8), s8])
        cv2.imwrite(str(self.dir / "compare_approved_vs_rebuilt.jpg"), cv2.cvtColor(side, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 93])
        layout = dict(post=self.num, canvas=dict(width=W, height=H, unit="px", dpi=72, colour="sRGB 8-bit"),
                      final_size=dict(width=1080, height=1350, how="Image > Image Size: 33.333%, Bicubic Sharper off / Automatic"),
                      import_rule="File > Place Embedded each PNG in order, position X=0 Y=0, scale 100% (all layers are full-canvas)",
                      layers=self.layers, svg=svg_files, check_vs_approved=check, **extra)
        (self.dir / "layout.json").write_text(json.dumps(layout, indent=1, ensure_ascii=False))
        print(self.num, len(self.layers), "layers", check)
        return check


# ------------------------------------------------------------------ SVG tracing
def trace_svg_path(alpha, M=None, up=4, eps=0.35):
    """outline path of a coverage mask (alpha 0..1), optionally mapped by a 2x3 affine M
    (mask px -> canvas px). Smooth: traced on a 4x Lanczos-enlarged mask at 0.5."""
    if up > 1:
        big = cv2.resize(alpha.astype(np.float32), None, fx=up, fy=up, interpolation=cv2.INTER_LANCZOS4)
    else:
        big = alpha.astype(np.float32)
    cnt, hier = cv2.findContours((big > 0.5).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    parts = []
    for c in cnt:
        if len(c) < 6: continue
        c = cv2.approxPolyDP(c, eps * up, True).reshape(-1, 2).astype(np.float64)
        if len(c) < 3: continue
        p = (c + 0.5) / up - 0.5
        if M is not None: p = p @ np.asarray(M)[:, :2].T + np.asarray(M)[:, 2]
        parts.append("M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in p) + " Z")
    return " ".join(parts)


def svg_doc(groups):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">\n' + "\n".join(groups) + "\n</svg>\n")


def rgbhex(c):
    c = np.clip(np.asarray(c), 0, 255).round().astype(int); return "#%02X%02X%02X" % tuple(c)


# ------------------------------------------------------------------ shared
def background(P, post):
    bg = cv2.cvtColor(cv2.imread(str(ROOT / "work/psd_assets/bg" / f"{post}_background.png")), cv2.COLOR_BGR2RGB).astype(np.float32)
    P.add("background", bg, np.ones((H, W), np.float32), "background",
          "navy / beige surface + every visible dot + the thread, rebuilt as vectors at 3x (tools/psd_assets/background_vector.py)",
          "source/background_supplied.jpg (surface colour), dots + thread measured on it")
    shutil.copyfile(ROOT / "work/psd_assets/bg" / f"{post}_dots_thread.svg", P.dir / "background_dots_thread.svg")


def card_content_3x(post, fid):
    cards = C.J("work/rebuild/cards.json")
    H_ = np.diag([K, K, 1]) @ np.array(cards[fid]["H_out"], np.float64)
    src = cv2.cvtColor(cv2.imread(str(C.WR / "site" / cards[fid]["file"])), cv2.COLOR_BGR2RGB).astype(np.float32)
    cut = C.CARD_BLANK_FROM.get(fid)
    if cut: src[cut:] = src[cut - 6:cut - 5]
    s = np.sqrt(abs(np.linalg.det(H_[:2, :2])))
    if s < 1: src = cv2.GaussianBlur(src, (0, 0), 0.45 / s)
    return cv2.warpPerspective(src, H_, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


# ------------------------------------------------------------------ posts 04-06
def export_0406(num):
    post = POSTS[num]; P = Post(num); style = C.STYLE[post]
    background(P, post)
    Pm = C.prints_union(post)
    gain = C.design_shadow(Pm, style) * C.enhance_shadow(Pm, post, sweep_on=False)
    P.add("shadow_prints_on_background", (0, 0, 0), 1 - gain, "shadow",
          "the prints' soft drop + contact shadow on the background (black, normal blend)")
    F = {f["id"]: f for f in C.J("work/rebuild/frames.json")[post]}
    below = np.zeros((H, W), np.float32)
    for fid in C.Z[post]:
        f = F[fid]
        outer = C.poly_mask(f["outer"], post); win = C.poly_mask(f["window"], post)
        if below.max() > 0:
            sh = C.design_shadow(outer, style)
            P.add(f"shadow_{fid}_on_prints_below", (0, 0, 0), (1 - sh) * below, "shadow",
                  f"the {fid} print's shadow where it lies on the prints under it")
        P.add(f"frame_{fid}", C.FRAME_WHITE, outer * (1 - win), "frame", "polaroid / card frame (white #FFFDF5)", "vector quad, work/rebuild/frames.json")
        if f["kind"] == "card":
            P.add(f"card_{fid}", card_content_3x(post, fid), outer * win, "screenshot",
                  "the configurator panel, live-site capture at 3x", f"work/rebuild/site/{C.J('work/rebuild/cards.json')[fid]['file']}")
        else:
            fn = RPL.SLOTS.get((post, fid), ("?",))[0]
            P.add(f"photo_{fid}", RPL.photo_content(post, fid), outer * win, "photo",
                  "the jacket photo, cover-fitted in the frame window", f"source/new_photos_l/{fn}")
        below = below + outer * (1 - below)
    # type + embroidery
    fit = C.J("work/rebuild/text/fit.json")
    col = {"navy": np.float32(C.NAVY), "cream": np.float32(C.CREAM), "red": np.float32(C.RED)}
    svg_groups, svg_edit = [], []
    sys.path.insert(0, str(ROOT / "tools/website_embroidery")); import run_pipeline as rp
    for r in C.RUNS[post]:
        if r.get("embroidered"):
            fits = {x["name"]: x for x in json.loads((rp.W / "dark_fit.json").read_text())}
            meta = json.loads((rp.W / "masks" / "meta.json").read_text())
            ff, m = fits[post], meta[post]; k = 600 / m["px"]
            M = C.to_out([[ff["sx"] * k, 0, ff["tx"] + ff["sx"] * (40 - m["pad"] * k)], [0, ff["sy"] * k, ff["ty"] + ff["sy"] * (40 - m["pad"] * k)]], post, 1)
            thread = rp.read_rgba(rp.W / "render" / post / "render_thread.png"); shadow = rp.read_rgba(rp.W / "render" / post / "render_shadow.png")
            dyed, _ = rp.dye(thread)
            wp = lambda x: cv2.warpAffine(x.astype(np.float32), M, (W, H), flags=cv2.INTER_AREA if np.hypot(M[0, 0], M[1, 0]) < 1 else cv2.INTER_CUBIC)
            t_a = np.clip(wp(thread[..., 3]), 0, 1); t_rgb = np.clip(wp(dyed * thread[..., 3:4]), 0, None) * 255; s_a = np.clip(wp(shadow[..., 3]), 0, 1)
            P.add(f"embroidery_{r['id']}_shadow", (0, 0, 0), s_a, "shadow", f"contact shadow of the embroidered word «{r['text']}»")
            P.add(f"embroidery_{r['id']}", t_rgb / np.maximum(t_a[..., None], 1e-4), t_a, "embroidery",
                  f"«{r['text']}»: the website 3D embroidery render (6x panel), crimson thread", f"work/website_embroidery/render/{post}")
            mk = cv2.imread(str(rp.W / "masks" / f"{post}_mask_x{rp.K}.png"), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255
            svg_groups.append(f'<g id="{r["id"]}_outline" fill="{rgbhex(C.RED)}" visibility="hidden"><!-- «{r["text"]}» letter outline (the visible word is the embroidery PNG) -->'
                              f'<path fill-rule="evenodd" d="{trace_svg_path(mk, M, up=1)}"/></g>')
            continue
        f = fit[r["id"]]
        m = cv2.imread(str(C.WR / "text" / f"{r['id']}_600.png"), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255
        M = C.to_out([[f["s"], 0, f["tx"]], [0, f["s"], f["ty"]]], post, 1)
        sc = np.hypot(M[0, 0], M[1, 0])
        a = cv2.warpAffine(cv2.GaussianBlur(m, (0, 0), max(0.3, 0.45 / sc)) if sc < 1 else m, M, (W, H), flags=cv2.INTER_LINEAR) * r.get("opacity", 1.0)
        P.add(f"text_{r['id']}", col[r["colour"]], a, "text", f"«{r['text']}» DARK ExtraBold, {rgbhex(col[r['colour']])}",
              "DARK-ExtraBold.ttf (jacketportable/public/assets/fonts/dark), browser-shaped")
        svg_groups.append(f'<g id="{r["id"]}" fill="{rgbhex(col[r["colour"]])}"><!-- «{r["text"]}» -->'
                          f'<path fill-rule="evenodd" d="{trace_svg_path(m, M)}"/></g>')
        ys, xs = np.nonzero(m > 0.5)
        x_r, y_b = xs.max() * M[0, 0] + M[0, 2], ys.max() * M[1, 1] + M[1, 2]
        y_t = ys.min() * M[1, 1] + M[1, 2]
        svg_edit.append(f'<text x="{x_r:.1f}" y="{y_t + 0.80 * (y_b - y_t):.1f}" direction="rtl" text-anchor="start" '
                        f'font-family="DARK" font-weight="800" font-size="{600 * sc:.1f}" fill="{rgbhex(col[r["colour"]])}">{r["text"]}</text>')
    # patches
    for n, c, D, rot, kind in C.PATCH_PLACE.get(post, pc.PLACE[post]):
        t, sh = pc.load(n)
        M = C.to_out(pc.matrix(t[..., 3], c, D, rot), post, 1)
        wp = lambda x, Mx=M: cv2.warpAffine(x, Mx, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        a = np.clip(wp(t[..., 3]), 0, 1); colr = wp(t[..., :3] * t[..., 3:4]) * 255; shw = np.clip(wp(sh), 0, 1)
        lf = pc.LIFT[style]
        Mo = C.to_out(pc.matrix(t[..., 3], (c[0] + lf["off"][0], c[1] + lf["off"][1]), D, rot), post, 1)
        lift = cv2.GaussianBlur(wp(t[..., 3], Mo), (0, 0), lf["sigma"] * C.S) * lf["k"]
        tone = cv2.resize(np.load(ROOT / f"work/psd_assets/tone_{post}_{n}.npy"), (W, H), interpolation=cv2.INTER_LINEAR)
        dark = 1 - np.clip(lift + shw * pc.CONTACT_K, 0, 0.85)
        P.add(f"patch_{n}_shadow", (0, 0, 0), 1 - dark, "shadow", f"{n} patch: soft lift shadow + contact shadow")
        P.add(f"patch_{n}", colr * tone[..., None] / np.maximum(a[..., None], 1e-4), a, "patch",
              f"embroidered {n} patch (website embroidery render of the supplied artwork)", f"work/patches/baked/{n}_thread.png")
    svg = ["text.svg"]
    (P.dir / "text.svg").write_text(svg_doc(['<g id="type_outlines"><!-- exact lettering as outlines, as approved -->'] + svg_groups + ["</g>",
        '<g id="type_editable" visibility="hidden"><!-- editable copies (needs the DARK font installed); position approximate: align them to the outlines -->'] + svg_edit + ["</g>"]))
    return P, svg


# ------------------------------------------------------------------ posts 01-03
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def matte_0103(post):
    """tools/quality/fix_quality.post_0103_fixed, at 3x"""
    import fix_quality as FQ
    p, a0, shade, bg = P3.split(post)
    a, _ = RB.strip_dashes(post, p, a0)
    killed = cv2.dilate(((a0 > 0.2) & (a < 0.05)).astype(np.uint8), np.ones((5, 5))) > 0
    a = np.where(killed & (a < 0.9), 0, a).astype(np.float32)
    ramp = np.clip((np.minimum(np.arange(shade.shape[1]), shade.shape[1] - 1 - np.arange(shade.shape[1])) - 4) / 4, 0, 1)
    shade_r = 1 + (shade - 1) * ramp[None, :]
    up = lambda x, i=cv2.INTER_LANCZOS4: P3.to_canvas(x, post, i)
    Pc = np.clip(up(p), 0, 255)
    Bold = np.clip(up(bg, cv2.INTER_LINEAR) * (up(shade - 1, cv2.INTER_LINEAR) + 1)[..., None], 0, 255)
    a_up = np.clip(up(a, cv2.INTER_LINEAR), 0, 1)
    resid = np.abs(Pc - (Pc @ RB.LUM / np.maximum(Bold @ RB.LUM, 1)).clip(0, 1.2)[..., None] * Bold).max(2)
    a_hi = smoothstep(7, 24, cv2.GaussianBlur(resid, (0, 0), 0.5 * K))
    band = cv2.dilate((a_up > 0.02).astype(np.uint8), np.ones((6 * K + 1, 6 * K + 1))) > 0
    core = cv2.erode((a_up > 0.98).astype(np.uint8), np.ones((4 * K + 1, 4 * K + 1))) > 0
    A = np.where(core, 1.0, a_hi * band)
    A = np.maximum(A, np.where(cv2.erode((a_up > 0.5).astype(np.uint8), np.ones((2 * K + 1, 2 * K + 1))) > 0, a_up, 0))
    inside = up(np.ones_like(a), cv2.INTER_NEAREST) > 0.5
    A = (A * inside * (up(killed.astype(np.float32), cv2.INTER_LINEAR) < 0.01)).astype(np.float32)
    if post == "POST_02":
        FQ.P3 = P3
        A, Pc = straight_frames_3x(post, A, Pc)
    Aa = np.maximum(A, 1e-3)[..., None]
    Fc = np.clip(np.where(A[..., None] > 0.05, (Pc - (1 - A[..., None]) * Bold) / Aa, Pc), 0, 255)
    Fc = np.clip(Fc + P3.SHARPEN * (Fc - cv2.GaussianBlur(Fc, (0, 0), 1.1 * K)), 0, 255)
    sh = up(shade_r - 1, cv2.INTER_LINEAR) + 1
    return A, Fc, sh


def straight_frames_3x(post, A, Pc):
    import fix_quality as FQ
    Fq = json.loads((ROOT / "work/quality_frames_post02.json").read_text())
    k2 = 2; mk = np.zeros((H * k2, W * k2), np.uint8)
    for f in Fq:
        q = (np.c_[np.array(f["outer"]), np.ones(4)] @ C.A(post, k2).T)[:, :2]
        cv2.fillPoly(mk, [np.int32(np.round(q * 16))], 255, cv2.LINE_AA, shift=4)
    U = cv2.resize(mk.astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_AREA); del mk
    edge = (U > 0.003) & (U < 0.997)
    band = cv2.dilate(edge.astype(np.uint8), np.ones((6 * K + 1, 6 * K + 1))) > 0
    keep = np.zeros_like(band)
    for x0, y0, x1, y1 in FQ.STICKERS_02:
        X0, Y0 = int(C.ox(post) + x0 * C.S), int(y0 * C.S); X1, Y1 = int(C.ox(post) + x1 * C.S), int(y1 * C.S)
        keep[Y0:Y1, X0:X1] = True
    big = np.array(Fq[0]["outer"]); bl, br = big[3], big[2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    xp, yp = (xx - C.ox(post)) / C.S, yy / C.S
    d = np.abs((br[0] - bl[0]) * (bl[1] - yp) - (bl[0] - xp) * (br[1] - bl[1])) / np.hypot(*(br - bl))
    keep |= d < 14
    sel = band & ~keep
    newP = np.where((sel & (U > A))[..., None], FQ.FRAME_WHITE * U[..., None] + Pc * (1 - U[..., None]), Pc)
    return np.where(sel, U, A).astype(np.float32), newP


def classify(Fc, A, lab, i, style):
    """text (flat type colour) / embroidery (red thread) / sticker-photo"""
    m = (lab == i) & (A > 0.9)
    if m.sum() < 50: m = (lab == i) & (A > 0.5)
    px = Fc[m]
    if len(px) == 0: return "artwork"
    med = np.median(px, 0); spread = np.percentile(np.abs(px - med).max(1), 75)
    red = (px[:, 0] - px[:, 2] > 80).mean()
    cream = np.array([252, 240, 214.]); navy = np.array([0, 48, 73.])
    if red > 0.6: return "embroidery"
    if spread < 22 and (np.abs(med - cream).max() < 30 or np.abs(med - navy).max() < 35): return "text"
    return "artwork"


# (name, kind, panel-px box of the element's centre, description / exact text)
ELEMENTS = {
    "POST_01": [("headline_jaketak", "text", (90, 90, 630, 228), "جاكيتك"),
                ("headline_hachaytak_embroidery", "embroidery", (30, 228, 590, 435), "حچايتك. (red embroidered lettering)"),
                ("sticker_error_windows", "sticker", (470, 430, 645, 585), "Error windows sticker"),
                ("sticker_idk_chatgpt", "sticker", (80, 485, 265, 585), "idk, ChatGPT it. sticker"),
                ("sticker_too_many_tabs", "sticker", (30, 660, 225, 850), "Too many brain tabs open! sticker"),
                ("text_001", "text", (480, 645, 630, 680), "[ 001 – أول نزلة ]"),
                ("text_line1", "text", (395, 688, 630, 730), "اسمك. رقمك. باجاتك."),
                ("text_line2", "text", (260, 733, 630, 775), "جاكيت واحد يتفصّل على كيفك.")],
    "POST_02": [("text_jacketek", "text", (250, 820, 420, 860), "JACKETEK"),
                ("polaroid_big", "print", (0, 0, 0, 0), "big polaroid: frame + group photo (flattened in the source)"),
                ("polaroid_left", "print", (0, 0, 0, 0), "left polaroid: frame + sleeve photo (flattened in the source)"),
                ("polaroid_right", "print", (0, 0, 0, 0), "right polaroid: frame + sleeve photo (flattened in the source)"),
                ("sticker_everything_under_ctrl", "sticker", (0, 0, 0, 0), "EVERYTHING IS UNDER Ctrl sticker"),
                ("sticker_uno_reverse", "sticker", (0, 0, 0, 0), "UNO reverse card sticker")],
    "POST_03": [("text_tafseela_01", "text", (430, 50, 630, 85), "تفصيلة 01 – حرف F مطرز"),
                ("sticker_thanks_chatgpt", "sticker", (0, 120, 120, 225), "THANKS CHATGPT I MADE IT sticker"),
                ("embroidery_tasmeemak", "embroidery", (220, 560, 540, 645), "تصميمك. (red embroidered lettering)"),
                ("text_min", "text", (540, 580, 630, 645), "من"),
                ("sticker_among_us", "sticker", (20, 645, 175, 755), "Among Us laptop sticker"),
                ("text_wayaeesh_wayak", "text", (200, 660, 590, 752), "ويعيش وياك."),
                ("decor_red_dashes", "decor", (195, 754, 590, 770), "red dashed underline")],
}
FRAMES02 = None
def _poly(post, pts):
    k2 = 2; mk = np.zeros((H * k2, W * k2), np.uint8)
    q = (np.c_[np.asarray(pts, float), np.ones(len(pts))] @ C.A(post, k2).T)[:, :2]
    cv2.fillPoly(mk, [np.int32(np.round(q * 16))], 255, cv2.LINE_AA, shift=4)
    return cv2.resize(mk.astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_AREA) > 0.5
def _frames02(post):
    global FRAMES02
    if FRAMES02 is None:
        Fq = json.loads((ROOT / "work/quality_frames_post02.json").read_text())
        FRAMES02 = {f["id"]: cv2.dilate(_poly(post, f["outer"]).astype(np.uint8), np.ones((7, 7))) > 0 for f in Fq}
    return FRAMES02
def _sticker(post, A, Fc, box):
    """a sticker's silhouette: the convex hull of its dark lettering / outline inside its box,
    grown by its white die-cut margin"""
    x0, y0, x1, y1 = box
    X0, Y0 = int(C.ox(post) + x0 * C.S), int(y0 * C.S); X1, Y1 = int(C.ox(post) + x1 * C.S), int(y1 * C.S)
    sub = (Fc[Y0:Y1, X0:X1] @ LUM < 205) & (A[Y0:Y1, X0:X1] > 0.5)
    lab, n = ndi.label(sub); sz = ndi.sum(sub, lab, range(1, n + 1))
    sub = np.isin(lab, 1 + np.flatnonzero(sz > 0.002 * sub.size))
    ys, xs = np.nonzero(sub)
    hull = cv2.convexHull(np.c_[xs, ys].astype(np.int32))
    hm = np.zeros(sub.shape, np.uint8); cv2.fillPoly(hm, [hull], 1)
    grown = cv2.dilate(hm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(6 * C.S) | 1, int(6 * C.S) | 1)))
    # the sticker's own palette (achromatic print + its silver die-cut rim, or the UNO red)
    # versus the photo it covers (green trees, blue sky): chroma decides, inside the grown hull
    px = Fc[Y0:Y1, X0:X1]
    chroma = px.max(2) - px.min(2)
    red = (px[..., 0] - px[..., 1] > 60) & (px[..., 0] > 120)
    own = ((chroma < 26) | red) & (grown > 0) & (A[Y0:Y1, X0:X1] > 0.3)
    own = cv2.morphologyEx(own.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5)))
    lab2, n2 = ndi.label(own)
    fgm = ndi.binary_fill_holes(lab2 == 1 + np.argmax(ndi.sum(own, lab2, range(1, n2 + 1)))) if n2 else hm > 0
    fgm = cv2.morphologyEx(fgm.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    fgm = ndi.binary_fill_holes(fgm)
    fgm = cv2.GaussianBlur(fgm.astype(np.float32), (0, 0), 1.0 * K) > 0.5     # smooth outline
    m = np.zeros((H, W), bool); m[Y0:Y1, X0:X1] = fgm
    return m & (A > 0.002)
SPLIT = {"POST_02": {
    "sticker_everything_under_ctrl": lambda post, A, Fc: _sticker(post, A, Fc, (20, 40, 150, 200)),
    "sticker_uno_reverse": lambda post, A, Fc: _sticker(post, A, Fc, (540, 70, 645, 200)),
    "polaroid_right": lambda post, A, Fc: _frames02(post)["right"] & (A > 0.002),
    "polaroid_left": lambda post, A, Fc: _frames02(post)["left"] & (A > 0.002),
    "polaroid_big": lambda post, A, Fc: _print_cluster(post, A)}}

def _print_cluster(post, A):
    """everything of the prints group not claimed by the stickers / small prints"""
    lab, n = ndi.label(A > 0.002)
    q = np.array(json.loads((ROOT / "work/quality_frames_post02.json").read_text())[0]["outer"]).mean(0)
    i = lab[int(q[1] * C.S), int(C.ox(post) + q[0] * C.S)]
    return lab == i
# split elements claim their pixels top-most first (stickers over the big print, small prints over it)
SPLIT_ORDER = {"POST_02": ["sticker_everything_under_ctrl", "sticker_uno_reverse", "polaroid_right", "polaroid_left", "polaroid_big"]}

NAMES_0103 = {   # element names by approximate centre (panel px): for readable layer names
    "POST_01": [((330, 115), "headline_jaketak"), ((300, 220), "headline_hachaytak_embroidery"), ((150, 315), "sticker_idk_chatgpt"),
                ((345, 300), "sticker_error_windows"), ((85, 450), "sticker_too_many_tabs"), ((385, 400), "text_001"),
                ((350, 430), "text_line1"), ((300, 455), "text_line2")],
    "POST_02": [((330, 280), "polaroid_big"), ((150, 630), "polaroid_left"), ((465, 615), "polaroid_right"),
                ((90, 115), "sticker_everything_under_ctrl"), ((590, 135), "sticker_uno_reverse"), ((335, 870), "text_jacketek")],
    "POST_03": [((520, 50), "text_tafseela_01"), ((150, 140), "sticker_thanks_chatgpt"), ((470, 560), "text_min_tasmeemak"),
                ((215, 635), "sticker_among_us"), ((500, 640), "text_wayaeesh_wayak"), ((500, 690), "decor_red_dashes")],
}


def name_for(post, cx, cy, kind, used):
    best, bd = None, 1e9
    for (x, y), nm in NAMES_0103.get(post, []):
        d = np.hypot(cx - x, cy - y)
        if d < bd: best, bd = nm, d
    nm = best if bd < 90 else f"{kind}_{int(cx)}_{int(cy)}"
    k = 2; base = nm
    while nm in used: nm = f"{base}_{k}"; k += 1
    used.add(nm); return nm


def export_0103(num):
    post = POSTS[num]; P = Post(num)
    background(P, post)
    A, Fc, sh = matte_0103(post)
    P.add("shadow_design", (0, 0, 0), np.clip(1 - sh, 0, 1), "shadow",
          "the design's own soft shadows under stickers, prints and type (from the approved post)")
    jk = None
    if post == "POST_03":
        import replace_f_post03 as JK
        Q = JK.QUAD.astype(np.float64); c = Q.mean(0); q = c + (Q - c) * 1.034
        kk = 4; mk = np.zeros((H * kk // 3 * 1, W * kk // 3 * 1), np.uint8)
        mk = np.zeros((1350 * 4 * K // 3 * 3 // 3, 1080 * 4 * K // 3 * 3 // 3), np.uint8)
        s4 = mk.shape[1] / 1080.0
        cv2.fillPoly(mk, [np.int32(np.round(q * s4 * 16))], 255, cv2.LINE_AA, shift=4)
        jkA = cv2.resize(mk.astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_AREA); del mk
        src = cv2.cvtColor(cv2.imread(str(ROOT / "source/jk_patch_post03.webp")), cv2.COLOR_BGR2RGB).astype(np.float32)
        h, w = src.shape[:2]; s = min(h, w); x0, y0 = (w - s) / 2, (h - s) / 2
        rect = np.float32([[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]])
        Hm = cv2.getPerspectiveTransform(rect, (q * K).astype(np.float32))
        sc = np.sqrt(abs(np.linalg.det(Hm[:2, :2])))
        src = cv2.GaussianBlur(src, (0, 0), 0.45 / sc) if sc < 1 else src
        tex = cv2.warpPerspective(src, Hm, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        jsh = cv2.GaussianBlur(cv2.warpAffine(jkA, np.float32([[1, 0, 3 * K], [0, 1, 5 * K]]), (W, H)), (0, 0), 5 * K) * 0.35 * (1 - jkA)
        jk = (jkA, tex, jsh, q)
        A = A * (1 - (jkA > 0.002))          # the old F patch under it: not exported
    # split into independent elements: components of the matte (letters of a line merged by a
    # 6 x 3 panel-px dilation), assigned to the named elements of ELEMENTS by their centre
    kern = cv2.getStructuringElement(cv2.MORPH_RECT, (int(6 * C.S), int(3 * C.S)))
    lab, n = ndi.label(cv2.dilate((A > 0.04).astype(np.uint8), kern))
    objs = ndi.find_objects(lab)
    assign = {}
    for i, sl in enumerate(objs, 1):
        if sl is None: continue
        m = (lab[sl] == i) & (A[sl] > 0.5)
        if m.sum() < 30 * K * K: continue
        ys, xs = np.nonzero(m)
        cx = (xs.mean() + sl[1].start - C.ox(post)) / C.S; cy = (ys.mean() + sl[0].start) / C.S
        hit = [e for e in ELEMENTS[post] if e[2][0] <= cx <= e[2][2] and e[2][1] <= cy <= e[2][3]]
        nm = hit[0][0] if hit else f"fragment_{int(cx)}_{int(cy)}"
        assign.setdefault(nm, []).append(i)
    region = {e[0]: e for e in ELEMENTS[post]}
    split = SPLIT.get(post, {})
    svg_groups = []
    names = [e[0] for e in ELEMENTS[post] if e[0] in assign or e[0] in split] + [k for k in assign if k not in region]
    claimed = np.zeros((H, W), bool); masks = []
    for nm in [x for x in SPLIT_ORDER.get(post, [])] + [x for x in names if x not in SPLIT_ORDER.get(post, [])]:
        if nm in split:
            m = split[nm](post, A, Fc) & ~claimed
        elif nm in assign:
            m = np.isin(lab, assign[nm]) & ~claimed
        else:
            continue
        claimed |= m; masks.append((nm, m))
    so = SPLIT_ORDER.get(post, [])
    masks = [x for x in masks if x[0] in so][::-1] + [x for x in masks if x[0] not in so]   # back to front
    for nm, m in masks:
        a = A * m
        if a.max() < 0.05: continue
        kind = region[nm][1] if nm in region else "artwork"
        src = "source/embroidery_reference_posts01-03.webp (the only source: 667 x 888 px for this post, enlarged 4.56x)"
        if kind == "text":
            colr = np.median(Fc[a > 0.9], 0)
            P.add(nm, Fc, a, "text", f"«{region[nm][3]}» lettering as in the approved post (its own pixels: shading + texture kept); clean vector outline in text.svg, colour {rgbhex(colr)}", src)
            svg_groups.append(f'<g id="{nm}" fill="{rgbhex(colr)}"><!-- «{region[nm][3]}» --><path fill-rule="evenodd" d="{trace_svg_path(a, None, up=2, eps=0.4)}"/></g>')
        else:
            P.add(nm, Fc, a, kind, region[nm][3] if nm in region else "small fragment in the approved post (e.g. a leftover guide-dash stub or a panel-edge sliver from the source), kept so the post stays identical; delete freely", src)
    if jk:
        jkA, tex, jsh, q = jk
        P.add("patch_JK_shadow", (0, 0, 0), jsh, "shadow", "soft contact shadow of the JK patch (light from the top left)")
        P.add("patch_JK", tex, jkA, "patch", "JK felt patch, square crop of the supplied photo on the approved quad", "source/jk_patch_post03.webp (2000 x 1778)")
    svg = []
    if svg_groups:
        (P.dir / "text.svg").write_text(svg_doc(['<g id="type_outlines"><!-- flat lettering traced from the post (font of 01-03 not available as a file) -->'] + svg_groups + ["</g>"]))
        svg = ["text.svg"]
    return P, svg


if __name__ == "__main__":
    nums = sys.argv[1:] or list(POSTS)
    report = {}
    for num in nums:
        post = POSTS[num]
        approved = cv2.cvtColor(cv2.imread(str(ROOT / "export/quality_fixed" / f"{num}.png")), cv2.COLOR_BGR2RGB)
        P, svg = (export_0406 if num in ("04", "05", "06") else export_0103)(num)
        svg.append("background_dots_thread.svg")
        report[num] = P.finish(svg, approved, {})
    (OUT / f"check_{'_'.join(nums)}.json").write_text(json.dumps(report, indent=1))
