"""JACKETEK — "the thread that tells your story" ad renderer.

Composites the whole 9:16 film frame by frame and pipes it to ffmpeg:
  * base plates: Kling clips (decoded with ffmpeg) or still photos moved by a
    virtual camera (the customisation scene uses the panel-accurate recolour
    variants from tools/ad/recolor.py),
  * ONE continuous burgundy thread drawn as animated paths (trim start/end,
    arrow heads, circle markers) that carries over every cut,
  * Iraqi-Arabic kinetic type (Cairo ExtraBold, shaped by raqm),
  * the logo stitch-on finale.

Usage:
  python3 render.py --clips DIR --out film.mp4            # final (all clips present)
  python3 render.py --preview --out preview.mp4           # stills stand in for clips
  python3 render.py --frames 10.0,24.5 --out-dir stills   # single frames (PNG)
Paths are relative to the repo root (or $JK_ROOT).
"""
import argparse
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(os.environ.get("JK_ROOT", Path(__file__).resolve().parents[2]))
W, H, FPS = 1080, 1920, 24

BEIGE = (253, 240, 213)          # #FDF0D5
BURG = (100, 21, 43)             # #64152B — jacketek configurator burgundy
RED = (193, 18, 31)              # #C1121F
INK_ON_DARK = (253, 240, 213)

FONT = ROOT / "work/ad/Cairo-ExtraBold.ttf"


# ----------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ramp(t, a, b):
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def lerp(a, b, u):
    return a + (b - a) * u


def keyed(t, keys, ease=ease_io):
    """keys: [(time, value or tuple)], piecewise eased interpolation."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0))
            if isinstance(v0, tuple):
                return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
            return lerp(v0, v1, u)
    return keys[-1][1]


# ----------------------------------------------------------------- geometry
def bezier(p0, p1, p2, p3, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = (np.array(p, float) for p in (p0, p1, p2, p3))
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def smooth_path(pts, n=24):
    """Catmull-Rom through pts -> dense polyline (N,2)."""
    pts = [np.array(p, float) for p in pts]
    if len(pts) < 3:
        return np.linspace(pts[0], pts[-1], n * 2)
    ext = [2 * pts[0] - pts[1]] + pts + [2 * pts[-1] - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return np.array(out)


def trim(poly, s, e):
    """Sub-polyline between arc-length fractions s..e."""
    if e <= s or len(poly) < 2:
        return None
    seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    L = cum[-1]
    a, b = s * L, e * L

    def at(d):
        i = int(np.clip(np.searchsorted(cum, d) - 1, 0, len(seg) - 1))
        u = (d - cum[i]) / seg[i] if seg[i] > 0 else 0
        return poly[i] + (poly[i + 1] - poly[i]) * u

    inner = poly[(cum > a) & (cum < b)]
    return np.vstack([at(a), inner, at(b)])


# ----------------------------------------------------------------- sources
class Clip:
    """Sequential frame reader for a video clip (24 fps). Local time -> frame."""

    def __init__(self, path, start=0.0, speed=1.0, reverse=False, fallback=None, zoom=(1.0, 1.06)):
        self.path, self.start, self.speed, self.reverse = path, start, speed, reverse
        self.fallback, self.zoom = fallback, zoom
        self.proc, self.idx, self.frame, self.frames = None, -1, None, None

    def _open(self):
        if self.reverse:
            # small: decode the used range fully, then index backwards
            cmd = ["ffmpeg", "-v", "error", "-ss", str(self.start), "-t", "6", "-i", str(self.path),
                   "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
            raw = subprocess.run(cmd, capture_output=True, check=True).stdout
            self.frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
            return
        cmd = ["ffmpeg", "-v", "error", "-ss", str(self.start), "-i", str(self.path),
               "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    def get(self, lt, dur):
        if self.fallback is not None:
            z = lerp(self.zoom[0], self.zoom[1], clamp(lt / max(dur, 0.01)))
            return still_zoom(self.fallback, z)
        if self.proc is None and self.frames is None:
            self._open()
        want = max(0, int(round(lt * self.speed * FPS)))
        if self.frames is not None:
            n = len(self.frames)
            # reverse: local 0 = last frame of the range dur*speed
            last = min(n - 1, int(round(dur * self.speed * FPS)))
            return self.frames[int(np.clip(last - want, 0, n - 1))]
        while self.idx < want:
            raw = self.proc.stdout.read(W * H * 3)
            if len(raw) < W * H * 3:
                break
            self.frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
            self.idx += 1
        return self.frame


def still_zoom(img, z, cx=0.5, cy=0.5):
    w, h = img.size
    cw, ch = w / z, h / z
    x0, y0 = cx * w - cw / 2, cy * h - ch / 2
    return np.array(img.transform((W, H), Image.Transform.EXTENT, (x0, y0, x0 + cw, y0 + ch), Image.BICUBIC))


class CamCanvas:
    """A big still canvas filmed by a virtual camera. Camera = (cx, cy, zoom)
    in 1x frame units (zoom 1 shows the 1080x1920 composition)."""

    def __init__(self, layers, scale=2):
        self.layers = layers            # dict name -> PIL RGB (W*scale x H*scale)
        self.s = scale

    def view(self, cam, name="base"):
        cx, cy, z = cam
        s = self.s
        cw, ch = W / z, H / z
        box = ((cx - cw / 2) * s, (cy - ch / 2) * s, (cx + cw / 2) * s, (cy + ch / 2) * s)
        return self.layers[name].transform((W, H), Image.Transform.EXTENT, box, Image.BICUBIC)

    @staticmethod
    def to_screen(cam, pts):
        cx, cy, z = cam
        pts = np.asarray(pts, float)
        return np.stack([(pts[:, 0] - cx) * z + W / 2, (pts[:, 1] - cy) * z + H / 2], 1)


# ----------------------------------------------------------------- assets
def beige_plate(w, h, seed=3):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx / w - 0.5) / 0.8) ** 2 + ((yy / h - 0.45) / 0.95) ** 2)
    t = np.clip(d, 0, 1)[..., None] ** 1.8
    img = np.array(BEIGE, float) * (1 - t) + np.array([0xEE, 0xDC, 0xB8], float) * t
    img += np.random.default_rng(seed).normal(0, 0.8, img.shape)
    return np.clip(img, 0, 255).astype(np.uint8)


def build_front_canvas():
    """2x canvas of the front composition (same framing as work/ad/frames/front_beige.png)
    for each recolour variant, plus the panel masks."""
    rec = ROOT / "work/ad/recolor"
    cut0 = Image.open(rec / "front_orig.png")
    bbox = cut0.getbbox()
    gx, gy, gs = (float(v) for v in (ROOT / "work/ad/frames/front_beige_geo.txt").read_text().split())
    S = 2
    scale = gs * S
    size = (round((bbox[2] - bbox[0]) * scale), round((bbox[3] - bbox[1]) * scale))
    pos = (round(gx * S), round(gy * S))
    plate = Image.fromarray(beige_plate(W * S, H * S))
    a = np.array(cut0.crop(bbox).resize(size, Image.LANCZOS))[..., 3].astype(float) / 255
    sh = Image.new("RGBA", plate.size, (0, 0, 0, 0))
    lay = Image.new("RGBA", size, (90, 40, 30, 0))
    lay.putalpha(Image.fromarray((a * 60).astype(np.uint8)))
    sh.alpha_composite(lay, (pos[0] + 12, pos[1] + 60))
    sh = sh.filter(ImageFilter.GaussianBlur(80))
    plate = plate.convert("RGBA")
    plate.alpha_composite(sh)
    layers = {}
    for name in ("front_orig", "front_sleeves", "front_sleeves_body"):
        im = Image.open(rec / f"{name}.png").crop(bbox).resize(size, Image.LANCZOS)
        p = plate.copy()
        p.alpha_composite(im, pos)
        layers[name] = p.convert("RGB")
    for name in ("mask_sleeves", "mask_body"):
        m = Image.open(rec / f"{name}.png").crop(bbox).resize(size, Image.LANCZOS)
        full = Image.new("L", plate.size, 0)
        full.paste(m, pos)
        layers[name] = full

    def to_canvas(px, py):      # source photo px -> 1x canvas coords
        return ((px - bbox[0]) * gs + gx, (py - bbox[1]) * gs + gy)

    # outer contour of the left sleeve (source px), for the thread to trace
    ms = np.array(Image.open(rec / "mask_sleeves.png")) > 128
    contour = []
    for y in range(470, 1660, 40):
        xs = np.where(ms[y, :1000])[0]
        if len(xs):
            contour.append(to_canvas(xs[0] - 18, y))
    # left body side seam (first body pixel from the left), bottom -> top
    mb = np.array(Image.open(rec / "mask_body.png")) > 128
    side = []
    for y in range(1600, 420, -60):
        xs = np.where(mb[y, :1000])[0]
        if len(xs):
            side.append(to_canvas(xs[0] + 40, y))
    return CamCanvas(layers, S), to_canvas, contour, side


# ----------------------------------------------------------------- thread drawing
class Stroke:
    def __init__(self, poly, s_keys, e_keys, arrow=False, width=7.0):
        self.poly, self.s_keys, self.e_keys, self.arrow, self.width = poly, s_keys, e_keys, arrow, width


def draw_strokes(img, strokes, offset=(0, 0)):
    """img: PIL RGB frame. strokes: list of (poly_screen, s, e, arrow, width, alpha)."""
    SS = 2
    layer = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for poly, s, e, arrow, width, alpha in strokes:
        sub = trim(poly, s, e)
        if sub is None or len(sub) < 2:
            continue
        pts = [((x + offset[0]) * SS, (y + offset[1]) * SS) for x, y in sub]
        halo = (253, 240, 213, int(150 * alpha))
        core = BURG + (int(255 * alpha),)
        d.line(pts, fill=halo, width=int((width + 6) * SS), joint="curve")
        for p in (pts[0], pts[-1]):
            r = (width + 6) * SS / 2
            d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=halo)
        d.line(pts, fill=core, width=int(width * SS), joint="curve")
        for p in (pts[0], pts[-1]):
            r = width * SS / 2
            d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=core)
        if arrow and e < 0.999:
            hx, hy = pts[-1]
            k = max(2, len(pts) // 12)
            bx, by = pts[-1 - min(k, len(pts) - 1)]
            ang = math.atan2(hy - by, hx - bx)
            for sgn in (-1, 1):
                a2 = ang + math.pi + sgn * 0.5
                q = (hx + math.cos(a2) * 30 * SS, hy + math.sin(a2) * 30 * SS)
                d.line([q, (hx, hy)], fill=halo, width=int((width + 6) * SS))
                d.line([q, (hx, hy)], fill=core, width=int(width * SS))
    layer = layer.reduce(SS)
    img.alpha_composite(layer) if img.mode == "RGBA" else img.paste(layer, (0, 0), layer)


def draw_marker(img, c, r, prog, alpha=1.0, offset=(0, 0)):
    if prog <= 0:
        return
    SS = 2
    x, y = (c[0] + offset[0]) * SS, (c[1] + offset[1]) * SS
    R = r * SS
    layer = Image.new("RGBA", (int(2 * R + 40 * SS), int(2 * R + 40 * SS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    ox, oy = layer.width / 2, layer.height / 2
    end = -90 + 360 * ease_out(prog)
    d.arc((ox - R, oy - R, ox + R, oy + R), -90, end, fill=(253, 240, 213, int(170 * alpha)), width=int(11 * SS))
    d.arc((ox - R, oy - R, ox + R, oy + R), -90, end, fill=BURG + (int(255 * alpha),), width=int(6 * SS))
    if prog > 0.6:
        rr = 7 * SS * ease_out((prog - 0.6) / 0.4)
        d.ellipse((ox - rr, oy - rr, ox + rr, oy + rr), fill=RED + (int(255 * alpha),))
    layer = layer.reduce(SS)
    img.paste(layer, (int(x / SS - layer.width / 2), int(y / SS - layer.height / 2)), layer)


# ----------------------------------------------------------------- typography
class Caption:
    """Iraqi-Arabic kinetic caption. Lines (\n = manual break) sit on a clean
    warm-beige label that wipes in right-to-left; words rise in RTL order; a
    short red accent draws under the last line."""

    def __init__(self, text, t0, t1, y, size=70, label=True):
        self.t0, self.t1, self.y, self.label = t0, t1, y, label
        font = ImageFont.truetype(str(FONT), size, layout_engine=ImageFont.Layout.RAQM)
        space = font.getlength(" ", direction="rtl", language="ar") * 1.05
        lh = size * 1.55
        asc, desc = font.getmetrics()
        self.items, self.lines, order = [], [], 0
        for li, line in enumerate(text.split("\n")):
            words = line.split(" ")
            ims = []
            for wd in words:
                l, t, r, b = font.getbbox(wd, direction="rtl", language="ar", anchor="ls")
                pad = 8
                im = Image.new("RGBA", (int(r - l + 2 * pad), int(b - t + 2 * pad)), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((pad - l, pad - t), wd, font=font, fill=BURG + (255,),
                                        direction="rtl", language="ar", anchor="ls")
                ims.append((im, r - l, -t, pad))
            lw = sum(i[1] for i in ims) + space * (len(ims) - 1)
            base_y = y + li * lh
            x = (W + lw) / 2
            first = order
            for im, w, a_, pad in ims:
                x -= w
                self.items.append((im, x - pad, base_y - a_ - pad, order))
                x -= space
                order += 1
            self.lines.append(((W - lw) / 2, (W + lw) / 2, base_y - asc * 0.78, base_y + desc * 0.55, first))
        self.n = order

    def draw(self, img, t, offset=(0, 0)):
        if t < self.t0 - 0.3 or t > self.t1 + 0.5:
            return
        out = ease_io(ramp(t, self.t1, self.t1 + 0.35))
        ox, oy = offset
        if self.label:
            lab = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(lab)
            for x0, x1, top, bot, first in self.lines:
                u = ease_io(ramp(t, self.t0 - 0.25 + first * 0.07, self.t0 + 0.2 + first * 0.07))
                if u <= 0:
                    continue
                padx, pady = 30, 16
                right = x1 + padx
                left = right - (x1 - x0 + 2 * padx) * u
                a = int(235 * (1 - out))
                d.rounded_rectangle((left + ox, top - pady + oy, right + ox, bot + pady + oy), 18, fill=BEIGE + (a,))
            img.alpha_composite(lab)
        for im, x, y, o in self.items:
            u = ease_out(ramp(t, self.t0 + o * 0.07, self.t0 + o * 0.07 + 0.42))
            a = u * (1 - out)
            if a <= 0.01:
                continue
            dy = (1 - u) * 26 - out * 14
            src = im
            if a < 0.999:
                src = im.copy()
                src.putalpha(Image.fromarray((np.array(im)[..., 3] * a).astype(np.uint8)))
            img.alpha_composite(src, (int(x + ox), int(y + dy + oy)))
        x0, x1, top, bot, _ = self.lines[-1]
        p = ease_io(ramp(t, self.t0 + 0.25 + self.n * 0.07, self.t0 + 0.75 + self.n * 0.07)) * (1 - out)
        if p > 0:
            cx = (x0 + x1) / 2
            d = ImageDraw.Draw(img)
            d.rectangle((cx + 40 - 80 * p + ox, bot + 26 + oy, cx + 40 + ox, bot + 32 + oy), fill=RED + (255,))


# ----------------------------------------------------------------- logo
def embroider(rgba, thread_rgb, angle=35, pitch=4.0):
    """Satin-stitch look for a flat logo layer: diagonal thread lines, raised
    relief from the alpha's distance field, soft drop shadow."""
    a = np.array(rgba)[..., 3].astype(float) / 255
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    th = math.radians(angle)
    u = (xx * math.cos(th) + yy * math.sin(th)) / pitch
    stripes = 0.5 + 0.5 * np.cos(u * 2 * math.pi)
    noise = np.random.default_rng(5).normal(0, 1, (h, w))
    noise = np.array(Image.fromarray(((noise * 30) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))) / 255 - 0.5
    blur = np.array(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))).astype(float) / 255
    gy, gx = np.gradient(blur)
    relief = np.clip(0.5 - (gx * 0.7 + gy * 1.0) * 6, 0, 1)
    shade = 0.78 + 0.22 * stripes + 0.12 * noise
    shade *= 0.75 + 0.5 * relief
    col = np.array(thread_rgb, float)[None, None, :] * shade[..., None]
    rgb = np.array(rgba)[..., :3].astype(float)
    tint = rgb / np.maximum(rgb.mean(axis=(0, 1), keepdims=True), 1)
    out = np.clip(col * np.where(a[..., None] > 0, 1.0, 0) * 1.0, 0, 255)
    out = np.where((np.abs(rgb - np.array(thread_rgb)).sum(-1) < 60)[..., None], out, np.clip(rgb * shade[..., None], 0, 255))
    res = np.concatenate([out, (a * 255)[..., None]], -1).astype(np.uint8)
    return Image.fromarray(res, "RGBA")


def build_logo(path, target_w=820):
    logo = Image.open(path).convert("RGBA")
    logo = logo.crop(logo.getbbox())
    s = target_w / logo.width
    logo = logo.resize((round(logo.width * s), round(logo.height * s)), Image.LANCZOS)
    stitched = embroider(logo, BURG)
    a = np.array(logo)[..., 3]
    al = Image.fromarray(a)
    ring = np.array(al.filter(ImageFilter.MaxFilter(5))).astype(int) - np.array(al.filter(ImageFilter.MinFilter(9))).astype(int)
    outline = (ring > 60)
    sh = Image.new("RGBA", (logo.width + 80, logo.height + 80), (0, 0, 0, 0))
    shadow = Image.new("RGBA", logo.size, (60, 20, 15, 0))
    shadow.putalpha(Image.fromarray((a * 0.45).astype(np.uint8)))
    sh.alpha_composite(shadow, (46, 52))
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    return stitched, outline, sh


def fabric_plate(seed=11):
    """Warm beige fabric (felt-like) background for the logo scene."""
    rng = np.random.default_rng(seed)
    base = beige_plate(W, H, seed).astype(float)
    n = rng.normal(0, 1, (H // 2, W // 2))
    n = np.array(Image.fromarray(((n * 40) + 128).clip(0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(1.2))).astype(float) / 255 - 0.5
    fib = rng.normal(0, 1, (H, W))
    fib = np.array(Image.fromarray(((fib * 50) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.BoxBlur(1))).astype(float) / 255 - 0.5
    img = base * (1 + 0.05 * n[..., None] + 0.035 * fib[..., None])
    return np.clip(img, 0, 255).astype(np.uint8)


def draw_needle(img, x, y_tip, alpha=1.0):
    """Shaded steel embroidery needle (+ clamp and presser foot) whose point
    sits at (x, y_tip)."""
    SS = 3
    w_, h_ = 200, 900
    lay = Image.new("RGBA", (w_ * SS, h_ * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, tip = w_ / 2 * SS, (h_ - 10) * SS
    A = int(255 * alpha)

    def steel(u):          # u: -1 (left edge) .. 1 (right edge) -> cylindrical shading
        k = 0.55 + 0.45 * math.cos((u + 0.35) * 1.4)
        return tuple(int(lerp(70, 245, k)) for _ in range(3))

    shaft_top, taper = 420 * SS, (h_ - 120) * SS
    for i in range(-10, 11):
        u = i / 10
        col = steel(u) + (A,)
        x0 = cx + u * 5.5 * SS
        # shaft
        d.line([(x0, shaft_top), (x0, taper)], fill=col, width=SS)
        # taper to the point
        d.line([(x0, taper), (cx + u * 0.6 * SS, tip)], fill=col, width=SS)
    d.ellipse((cx - 1.6 * SS, 700 * SS, cx + 1.6 * SS, 724 * SS), fill=(40, 40, 44, A))      # eye
    # clamp block + screw
    for i in range(-20, 21):
        u = i / 20
        d.line([(cx + u * 26 * SS, 250 * SS), (cx + u * 26 * SS, shaft_top + 8 * SS)], fill=steel(u) + (A,), width=SS)
    d.ellipse((cx + 22 * SS, 300 * SS, cx + 48 * SS, 326 * SS), fill=(30, 30, 34, A))
    # presser foot hovering just above the fabric
    d.rounded_rectangle((cx - 70 * SS, (h_ - 70) * SS, cx - 14 * SS, (h_ - 52) * SS), 6 * SS, fill=(150, 152, 158, int(A * 0.9)))
    d.rounded_rectangle((cx + 14 * SS, (h_ - 70) * SS, cx + 70 * SS, (h_ - 52) * SS), 6 * SS, fill=(150, 152, 158, int(A * 0.9)))
    d.line([(cx - 40 * SS, 560 * SS), (cx - 40 * SS, (h_ - 62) * SS)], fill=(130, 132, 138, int(A * 0.9)), width=7 * SS)
    lay = lay.reduce(SS)
    # soft contact shadow of the needle tip on the fabric
    img.alpha_composite(lay, (int(x - w_ / 2), int(y_tip - (h_ - 10))))


# ================================================================= timeline
COPY = [
    "كل تخرّج إله حچايتَه…",
    "إنت تختار لون البودي والكمّ…",
    "وحتى التفاصيل الصغيرة،\nإلك بيها اختيار.",
    "حروفك، اسمك،\nوتصميم يمثّلك.",
    "تفاصيلك على الكمّ…",
    "وخلي الظهر يحچي عنك.",
    "مو طباعة…\nتطريز، غرزة ورا غرزة.",
    "كل تفصيلة اخترتها…\nصارت جزء من حچايتك.",
    "جاكيتك حچايتك",
]
TOTAL = 44.0


class Shot:
    def __init__(self, t0, t1, base, strokes=None, markers=None, captions=None, extra=None):
        self.t0, self.t1 = t0, t1
        self.base = base                  # f(lt) -> HxWx3 uint8 (or PIL)
        self.strokes = strokes or (lambda lt: [])   # f(lt) -> [(poly, s, e, arrow, width, alpha)]
        self.markers = markers or (lambda lt: [])   # f(lt) -> [(center, r, prog, alpha)]
        self.captions = captions or []
        self.extra = extra                # f(img, lt, offset) for scene-specific overlays

    @property
    def dur(self):
        return self.t1 - self.t0


def S(poly):
    return np.asarray(poly, float)


def build(args):
    clips = Path(args.clips) if args.clips else None
    prev = args.preview

    def clip(name, start=0.0, fallback=None, **kw):
        if prev or clips is None or not (clips / name).exists():
            fb = Image.open(ROOT / fallback).convert("RGB").resize((W, H), Image.LANCZOS) if fallback else \
                Image.fromarray(beige_plate(W, H))
            return Clip(None, start, fallback=fb, **kw)
        return Clip(clips / name, start, **kw)

    shots = []

    # ---- S1 0.0-3.6 opening: Kling push-in on the warm beige jacket ----------
    c1 = clip("k_open.mp4", 0, "work/ad/frames/front_beige.png", zoom=(1.0, 2.0))
    p1 = smooth_path([(-40, 1560), (180, 1420), (330, 1200), (380, 1000), (430, 905)])
    shots.append(Shot(0.0, 3.6, lambda lt: c1.get(lt, 3.6),
                      strokes=lambda lt: [(p1, 0.0, ease_io(ramp(lt, 0.25, 2.9)), True, 7, 1.0)],
                      captions=[Caption(COPY[0], 0.45, 2.75, 175)]))

    # ---- S2+S3 3.6-14.0 the customisation canvas (real photo, virtual camera) -
    canvas, to_canvas, sleeve_contour, body_side = build_front_canvas()
    cam_keys = [(0.0, (618.0, 793.0, 2.2)), (0.8, (540.0, 985.0, 1.12)), (5.2, (540.0, 975.0, 1.17)),
                (6.9, (565.0, 560.0, 2.15)),                                       # collar
                (8.0, (565.0, 560.0, 2.2)),
                (8.7, to_canvas(1660, 1660) + (1.95,)),                            # right cuff
                (9.2, to_canvas(1660, 1660) + (2.0,)),
                (9.8, to_canvas(820, 1700) + (1.9,)),                              # waistband
                (10.4, to_canvas(820, 1700) + (1.92,))]
    cam_keys = [(t, tuple(float(v) for v in c)) for t, c in cam_keys]

    def cam_at(lt):
        return keyed(lt, cam_keys)

    sl_top = sleeve_contour[0]
    sl_bot = sleeve_contour[-1]
    head_s1 = np.array([430.0, 905.0])
    c0 = cam_keys[0][1]
    entry = (c0[0] + (head_s1[0] - W / 2) / c0[2], c0[1] + (head_s1[1] - H / 2) / c0[2])
    q_entry = smooth_path([entry, (entry[0] - 40, entry[1] - 80), (sl_top[0] - 30, sl_top[1] - 60), sl_top])
    q_sleeve = smooth_path(sleeve_contour, 6)
    cuff_l = to_canvas(330, 1700)
    q_cross = smooth_path([sl_bot, (cuff_l[0] + 30, cuff_l[1] + 10), (body_side[0][0] - 10, body_side[0][1] + 40),
                           body_side[0]])
    q_side = smooth_path(body_side, 6)
    collar = to_canvas(1040, 240)
    cuff_r = to_canvas(1660, 1760)
    waist = to_canvas(780, 1795)
    q_collar = smooth_path([body_side[-1], (body_side[-1][0] + 40, collar[1] - 40), (collar[0] - 140, collar[1] - 70),
                            (collar[0] - 120, collar[1] + 10)])
    q_cuff = smooth_path([(collar[0] + 120, collar[1] + 30), (collar[0] + 300, collar[1] + 300),
                          (cuff_r[0] + 70, cuff_r[1] - 300), (cuff_r[0] + 60, cuff_r[1] - 60)])
    q_waist = smooth_path([(cuff_r[0] - 60, cuff_r[1] + 30), (cuff_r[0] - 200, cuff_r[1] + 90),
                           (waist[0] + 200, waist[1] + 90), (waist[0] + 90, waist[1] + 40)])
    # exit: run right along the hem and off the frame (screen x > W) for the push
    q_exit = smooth_path([(waist[0] + 120, waist[1] - 30), (waist[0] + 400, waist[1] - 120), (waist[0] + 760, waist[1] - 140)])

    rec_t = {"sleeve": (1.0, 2.2), "body": (2.6, 4.0), "back": (5.4, 5.9)}
    ms = np.array(canvas.layers["mask_sleeves"]).astype(float) / 255
    mb = np.array(canvas.layers["mask_body"]).astype(float) / 255
    L0 = np.array(canvas.layers["front_orig"]).astype(np.float32)
    L1 = np.array(canvas.layers["front_sleeves"]).astype(np.float32)
    L2 = np.array(canvas.layers["front_sleeves_body"]).astype(np.float32)
    yy2 = np.arange(H * 2, dtype=np.float32)[:, None]
    xx2 = np.arange(W * 2, dtype=np.float32)[None, :]
    sl_y0, sl_y1 = sleeve_contour[0][1] * 2, sleeve_contour[-1][1] * 2
    bs0 = np.array(body_side[len(body_side) // 2]) * 2
    rr = np.sqrt((xx2 - bs0[0]) ** 2 + (yy2 - bs0[1]) ** 2)
    cache = {}

    def canvas_base(lt):
        cam = cam_at(lt)
        ws = ease_io(ramp(lt, *rec_t["sleeve"]))
        wb = ease_io(ramp(lt, *rec_t["body"]))
        back = ease_io(ramp(lt, *rec_t["back"]))
        key = (round(ws, 3), round(wb, 3), round(back, 3))
        if key not in cache:
            cache.clear()
            yfront = lerp(sl_y0 - 80, sl_y1 + 80, ws)
            wsm = np.clip((yfront - yy2) / 90, 0, 1) * ms if 0 < ws < 1 else (ms if ws >= 1 else ms * 0)
            rad = wb * 2600
            wbm = np.clip((rad - rr) / 140, 0, 1) * mb if 0 < wb < 1 else (mb if wb >= 1 else mb * 0)
            img = L0 + (L1 - L0) * wsm[..., None]
            img = img + (L2 - L1) * wbm[..., None]          # L2-L1 is non-zero on the body only
            img = img * (1 - back) + L0 * back
            cache[key] = Image.fromarray(img.astype(np.uint8))
        im = cache[key]
        cx, cy, z = cam
        cw, ch = W / z, H / z
        return np.array(im.transform((W, H), Image.Transform.EXTENT,
                                     ((cx - cw / 2) * 2, (cy - ch / 2) * 2, (cx + cw / 2) * 2, (cy + ch / 2) * 2),
                                     Image.BICUBIC))

    def canvas_strokes(lt):
        cam = cam_at(lt)
        T = lambda q: CamCanvas.to_screen(cam, q)
        fade_all = 1 - ease_io(ramp(lt, 5.6, 6.2))      # contour lines leave as the camera moves on
        out = [
            (T(q_entry), ease_io(ramp(lt, 0.5, 1.4)), ease_io(ramp(lt, 0.0, 1.0)), False, 7, 1.0),
            (T(q_sleeve), ease_io(ramp(lt, 5.0, 5.9)), ease_io(ramp(lt, 0.95, 2.2)), True, 7, fade_all or 0.0),
            (T(q_cross), ease_io(ramp(lt, 5.0, 5.9)), ease_io(ramp(lt, 2.2, 2.7)), False, 7, 1.0),
            (T(q_side), ease_io(ramp(lt, 5.2, 6.1)), ease_io(ramp(lt, 2.6, 3.9)), True, 7, 1.0),
            (T(q_collar), ease_io(ramp(lt, 7.2, 7.9)), ease_io(ramp(lt, 5.4, 6.8)), True, 7, 1.0),
            (T(q_cuff), ease_io(ramp(lt, 8.6, 9.0)), ease_io(ramp(lt, 7.6, 8.6)), True, 7, 1.0),
            (T(q_waist), ease_io(ramp(lt, 9.5, 9.9)), ease_io(ramp(lt, 8.9, 9.7)), True, 7, 1.0),
            (T(q_exit), 0.0, ease_io(ramp(lt, 9.6, 10.3)), False, 7, 1.0),
        ]
        return out

    def canvas_markers(lt):
        cam = cam_at(lt)
        T = lambda p: CamCanvas.to_screen(cam, [p])[0]
        mid_sleeve = sleeve_contour[len(sleeve_contour) // 2]
        m = []
        a1 = 1 - ease_io(ramp(lt, 4.6, 5.0))
        m.append((T((mid_sleeve[0] + 90, mid_sleeve[1])), 70, ramp(lt, 2.0, 2.6), a1))
        m.append((T((body_side[len(body_side) // 2][0] + 150, body_side[len(body_side) // 2][1])), 70, ramp(lt, 3.8, 4.4), a1))
        m.append((T(collar), 150, ramp(lt, 6.8, 7.4), 1 - ease_io(ramp(lt, 7.9, 8.3))))
        m.append((T(cuff_r), 120, ramp(lt, 8.5, 9.0), 1 - ease_io(ramp(lt, 9.3, 9.6))))
        m.append((T(waist), 120, ramp(lt, 9.6, 10.0), 1 - ease_io(ramp(lt, 10.2, 10.4))))
        return m

    shots.append(Shot(3.6, 14.0, canvas_base, canvas_strokes, canvas_markers,
                      captions=[Caption(COPY[1], 0.9, 5.0, 170), Caption(COPY[2], 6.0, 10.0, 1560)]))

    # ---- S4 14.0-17.4 chest embroidery -----------------------------------------
    c4 = clip("c2.mp4", 0, "work/reel/frames/s2_chest.png")
    p4 = smooth_path([(-30, 796), (90, 900), (160, 1110), (420, 1140), (760, 1150), (960, 1190), (1120, 1240)])
    shots.append(Shot(14.0, 17.4, lambda lt: c4.get(lt, 3.4),
                      strokes=lambda lt: [(p4, ease_io(ramp(lt, 2.0, 3.3)), ease_io(ramp(lt, -0.25, 3.15)), False, 7, 1.0)],
                      markers=lambda lt: [((500, 840), 330, ramp(lt, 0.9, 1.7), 1 - ease_io(ramp(lt, 2.6, 3.0)))],
                      captions=[Caption(COPY[3], 0.45, 3.0, 1560)]))

    # ---- S5 17.4-20.8 sleeve number --------------------------------------------
    c5 = clip("k_09.mp4", 0, "work/ad/frames/sleeve09.png")
    track = [(0.0, (297.0, 809.0)), (1.7, (410.0, 809.0)), (3.4, (470.0, 782.0))]
    p5 = smooth_path([(-30, 1240), (150, 1160), (330, 1110), (560, 1110), (800, 1080), (1120, 1060)])
    shots.append(Shot(17.4, 20.8, lambda lt: c5.get(lt, 3.4),
                      strokes=lambda lt: [(p5, ease_io(ramp(lt, 2.0, 3.35)), ease_io(ramp(lt, -0.25, 3.2)), False, 7, 1.0)],
                      markers=lambda lt: [(keyed(lt, track, ease=lambda x: x), 250, ramp(lt, 0.6, 1.4),
                                           1 - ease_io(ramp(lt, 2.7, 3.1)))],
                      captions=[Caption(COPY[4], 0.4, 3.0, 1560)]))

    # ---- S6 20.8-24.2 the back -------------------------------------------------
    c6 = clip("c6.mp4", 0, "work/reel/frames/s4_back.png")
    p6 = smooth_path([(-30, 1060), (60, 1240), (240, 1420), (560, 1460), (880, 1380), (1000, 900), (1060, 600), (1120, 470)])
    shots.append(Shot(20.8, 24.2, lambda lt: c6.get(lt, 3.4),
                      strokes=lambda lt: [(p6, ease_io(ramp(lt, 2.2, 3.4)), ease_io(ramp(lt, -0.25, 3.2)), False, 7, 1.0)],
                      captions=[Caption(COPY[5], 0.4, 3.0, 1620)]))

    # ---- S7 24.2-31.4 graphic line becomes real thread, then the machine -------
    e1 = clip("k_emb1.mp4", 0, None)
    e2 = clip("k_emb2.mp4", 1.0, None)
    e3 = clip("c5b.mp4", 1.5, "work/reel/frames/s3_patch.png")
    e4 = clip("c5_v1.mp4", 2.6, "work/reel/frames/s3_macro.png")
    real = smooth_path([(-30, 452), (200, 600), (400, 770), (560, 910), (620, 964)])

    def emb_base(lt):
        if lt < 2.8:
            return e1.get(max(0.0, lt - 0.8), 2.0)
        if lt < 4.4:
            return e2.get(lt - 2.8, 1.6)
        if lt < 5.8:
            return e3.get(lt - 4.4, 1.4)
        return e4.get(lt - 5.8, 1.4)

    def emb_strokes(lt):
        a = 1 - ease_io(ramp(lt, 0.85, 1.35))
        out = []
        if a > 0:
            out.append((real, 0.0, ease_io(ramp(lt, -0.25, 0.8)), False, 6, a))
        # the thread leaves the last macro toward the finished jacket
        out.append((smooth_path([(330, 1500), (200, 1650), (90, 1800), (-40, 1960)]), 0.0,
                    ease_io(ramp(lt, 6.5, 7.2)), False, 7, 1.0))
        return out

    shots.append(Shot(24.2, 31.4, emb_base, emb_strokes, captions=[Caption(COPY[6], 1.1, 6.6, 1600)]))

    # ---- S8 31.4-37.4 the finished jacket: front pull-back, then the back ------
    r1 = clip("k_reveal.mp4", 0, "work/ad/frames/front_beige.png", zoom=(1.6, 1.0))
    back_img = Image.open(ROOT / "source/video_refs/jk_back.webp").convert("RGB")
    sb = H / back_img.height

    def back_pan(lt):
        u = ease_io(clamp(lt / 2.2))
        cx = lerp(560, 900, u)
        cw = W / sb
        return np.array(back_img.transform((W, H), Image.Transform.EXTENT,
                                           (cx - cw / 2, 0, cx + cw / 2, back_img.height), Image.BICUBIC))

    p8 = smooth_path([(-40, 1900), (60, 1700), (150, 1350), (110, 900), (240, 420), (620, 240), (960, 420), (1120, 700)])
    shots.append(Shot(31.4, 35.4, lambda lt: r1.get(lt, 4.0),
                      strokes=lambda lt: [(p8, ease_io(ramp(lt, 2.6, 3.9)), ease_io(ramp(lt, -0.3, 3.6)), False, 7, 1.0)],
                      captions=[Caption(COPY[7], 0.7, 5.6, 1660)]))
    p8b = smooth_path([(-30, 700), (200, 620), (500, 600), (800, 640), (1120, 980)])
    shots.append(Shot(35.4, 37.4, back_pan,
                      strokes=lambda lt: [(p8b, ease_io(ramp(lt, 1.2, 2.1)), ease_io(ramp(lt, -0.25, 1.9)), False, 7, 1.0)]))

    # ---- S9 37.4-44.0 the thread embroiders the logo -----------------------------
    fab = Image.fromarray(fabric_plate())
    logo_path = Path(args.logo) if args.logo else ROOT / "work/ad/logo/logo_interim.png"
    stitched, outline, lshadow = build_logo(logo_path)
    lw, lh_ = stitched.size
    lx, ly = (W - lw) // 2, int(H * 0.44 - lh_ / 2)
    sa = np.array(stitched)
    outline_rgba = sa.copy()
    outline_rgba[..., 3] = np.where(outline, sa[..., 3], 0)
    jag = np.random.default_rng(9).normal(0, 6, lh_)[:, None]
    xs = np.arange(lw)[None, :]
    slogan = Caption(COPY[8], 4.3, 99, int(H * 0.44 + lh_ / 2 + 150), size=88, label=False)

    def logo_frame(lt):
        img = fab.copy().convert("RGBA")
        f1 = ease_io(ramp(lt, 0.9, 2.9)) * (lw + 40) - 20      # outline front
        f2 = ease_io(ramp(lt, 2.5, 4.3)) * (lw + 40) - 20      # fill front
        m1 = (xs + jag < f1)
        m2 = (xs + jag < f2)
        if f2 > -20:
            sh = lshadow.copy()
            k = np.array(sh)[..., 3].astype(float) * clamp(f2 / lw)
            sh.putalpha(Image.fromarray(k.astype(np.uint8)))
            img.alpha_composite(sh, (lx - 40, ly - 40))
        o = outline_rgba.copy()
        o[..., 3] = (o[..., 3] * m1).astype(np.uint8)
        img.alpha_composite(Image.fromarray(o), (lx, ly))
        fl = sa.copy()
        fl[..., 3] = (fl[..., 3] * m2).astype(np.uint8)
        img.alpha_composite(Image.fromarray(fl), (lx, ly))
        # needle rides the stitching front, bobbing like a machine needle
        if 0.8 < lt < 4.8:
            front = f1 if lt < 2.75 else f2
            nx = lx + clamp(front, 0, lw)
            bob = 12 * (0.5 + 0.5 * math.sin(lt * 2 * math.pi * 11))
            lift = ease_io(ramp(lt, 4.3, 4.8)) * 900
            a = 1 - ease_io(ramp(lt, 4.4, 4.8))
            draw_needle(img, nx, ly + lh_ * 0.5 - bob - lift, a)
        # gentle push-in for the hold
        z = 1 + 0.035 * ease_io(ramp(lt, 3.8, 6.6))
        if z > 1.0005:
            cw, ch = W / z, H / z
            img = img.transform((W, H), Image.Transform.EXTENT,
                                ((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2), Image.BICUBIC)
        return np.array(img.convert("RGB"))

    def logo_strokes(lt):
        # the thread runs in from the left and feeds the needle at the stitching front
        f1 = ease_io(ramp(lt, 0.9, 2.9)) * (lw + 40) - 20
        f2 = ease_io(ramp(lt, 2.5, 4.3)) * (lw + 40) - 20
        front = clamp(f1 if lt < 2.75 else f2, 0, lw)
        bob = 12 * (0.5 + 0.5 * math.sin(lt * 2 * math.pi * 11))
        nx, ny = lx + front, ly + lh_ * 0.5 - bob - 180          # the needle's eye
        p = smooth_path([(-30, 980), (220, 960), (nx - 200, ny + 40), (nx, ny)], 16)
        a = 1 - ease_io(ramp(lt, 4.3, 4.8))
        return [(p, 0.0, ease_io(ramp(lt, -0.25, 0.9)), False, 6, a)]

    shots.append(Shot(37.4, 44.0, logo_frame, logo_strokes, captions=[slogan]))
    return shots


TRANSITIONS = {   # cut time -> (kind, duration)
    3.6: ("fade", 0.3), 14.0: ("push", 0.5), 17.4: ("push", 0.45), 20.8: ("push", 0.45),
    24.2: ("push", 0.5), 31.4: ("fade", 0.35), 35.4: ("push", 0.45), 37.4: ("push", 0.5),
}


def frame_at(shots, t):
    # which cut (if any) is in progress
    for cut, (kind, d) in TRANSITIONS.items():
        if cut - d / 2 <= t < cut + d / 2:
            a = next(s for s in shots if abs(s.t1 - cut) < 1e-6)
            b = next(s for s in shots if abs(s.t0 - cut) < 1e-6)
            u = ease_io((t - (cut - d / 2)) / d)
            fa, fb = np.asarray(a.base(t - a.t0)), np.asarray(b.base(t - b.t0))
            if kind == "fade":
                base = (fa * (1 - u) + fb * u).astype(np.uint8)
                img = Image.fromarray(base).convert("RGBA")
                overlay(img, a, t - a.t0, (0, 0))
                overlay(img, b, t - b.t0, (0, 0))
                return img
            dx = int(round(W * u))
            base = np.concatenate([fa[:, dx:], fb[:, :dx]], axis=1)
            img = Image.fromarray(base).convert("RGBA")
            overlay(img, a, t - a.t0, (-dx, 0))
            overlay(img, b, t - b.t0, (W - dx, 0))
            return img
    s = next(s for s in shots if s.t0 <= t < s.t1)
    img = Image.fromarray(np.asarray(s.base(t - s.t0))).convert("RGBA")
    overlay(img, s, t - s.t0, (0, 0))
    return img


def overlay(img, shot, lt, off):
    st = [x for x in shot.strokes(lt) if x[5] > 0.01]
    if st:
        draw_strokes(img, st, off)
    for c, r, p, a in shot.markers(lt):
        if a > 0.01:
            draw_marker(img, c, r, p, a, off)
    for cap in shot.captions:
        cap.draw(img, lt, off)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips")
    ap.add_argument("--logo")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--out", default="jacketek_ad.mp4")
    ap.add_argument("--frames", help="comma separated times -> PNGs instead of a video")
    ap.add_argument("--out-dir", default="frames")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=TOTAL)
    args = ap.parse_args()
    shots = build(args)
    if args.frames:
        Path(args.out_dir).mkdir(parents=True, exist_ok=True)
        for t in [float(v) for v in args.frames.split(",")]:
            frame_at(shots, t).convert("RGB").save(Path(args.out_dir) / f"f_{t:05.2f}.png")
        return
    n0, n1 = int(round(args.start * FPS)), int(round(args.end * FPS))
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
                            "-profile:v", "high", "-pix_fmt", "yuv420p", "-movflags", "+faststart", args.out],
                           stdin=subprocess.PIPE)
    for n in range(n0, n1):
        enc.stdin.write(frame_at(shots, n / FPS).convert("RGB").tobytes())
        if n % 48 == 0:
            print(f"{n / FPS:5.1f}s", file=sys.stderr, flush=True)
    enc.stdin.close()
    enc.wait()


if __name__ == "__main__":
    main()
