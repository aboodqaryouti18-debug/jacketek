"""JACKETEK post background treatment.

Recreates the reference background ("taatheer el background"): very faint thin
vertical lines plus a soft, diffused depth concentrated at the centre of each
post, fading to nothing at all four edges.

Everything is expressed as pure brightness gain (multiply / colour-dodge
style), so the hue and chroma of the brand beige and navy are never changed --
only their lightness moves by a few percent.

Outputs
  export/layers_1080x1350/  editable layers for the real 1080x1350 source files
  export/posts/             each post with the treatment applied
  export/grid/              the three-post grid preview (before / after)

Usage:  python3 tools/background_treatment.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC_GRID = ROOT / "source" / "grid_preview_original.webp"
OUT = ROOT / "export"

# Panel x-ranges inside the grid preview (measured from the navy panel edges).
PANELS = {
    "POST_04": (0, 667),
    "POST_05": (667, 1333),
    "POST_06": (1333, 2000),
}

# Per-post settings. depth < 0 darkens the centre (soft shadow, as in the
# reference); depth > 0 lifts it (soft glow -- reads as depth on navy).
SETTINGS = {
    "beige": dict(depth=-0.055, line_dark=0.030, line_light=0.010),
    "navy": dict(depth=+0.16, line_dark=0.10, line_light=0.05),
}
POST_STYLE = {"POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}

LINES_PER_WIDTH = 21.5   # reference: ~33 px spacing on a 709 px canvas


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def center_mask(w, h):
    """Soft centred falloff: 1 at the centre, exactly 0 on every edge."""
    y, x = np.mgrid[0:h, 0:w].astype(np.float64)
    u = (x + 0.5) / w * 2 - 1            # -1..1
    v = (y + 0.5) / h * 2 - 1
    # Wide elliptical gaussian -> no visible circle.
    g = np.exp(-((u / 0.66) ** 2 + (v / 0.64) ** 2))
    # Long, gentle edge window guarantees a calm border on all four sides
    # without introducing a visible rounded-box shape.
    win = smoothstep(-0.1, 0.9, 1 - np.abs(u)) * smoothstep(-0.1, 0.9, 1 - np.abs(v))
    m = g * win
    return m / m.max()


def line_profiles(w, h):
    """Thin vertical lines: a 1 px dark core with a faint light halo, like the
    reference. Returns (dark, light) maps in 0..1."""
    spacing = w / LINES_PER_WIDTH
    x = np.arange(w) + 0.5
    # distance (px) to nearest line, lines offset half a spacing from edges
    d = np.abs(((x - spacing / 2) % spacing) - spacing / 2)
    s = w / 709.0                         # scale line width with canvas size
    dark = np.exp(-(d / (0.65 * s)) ** 2)
    light = np.exp(-((d - 2.2 * s) / (1.1 * s)) ** 2) * (d > 0.8 * s)
    # lines fade gently toward top and bottom like printed paper
    y = (np.arange(h) + 0.5) / h
    vfade = 0.55 + 0.45 * smoothstep(0.0, 0.25, y) * smoothstep(0.0, 0.25, 1 - y)
    return dark[None, :] * vfade[:, None], light[None, :] * vfade[:, None]


def gain_map(w, h, style):
    """Total brightness gain (1.0 = unchanged) for one post canvas."""
    cfg = SETTINGS[style]
    m = center_mask(w, h)
    dark, light = line_profiles(w, h)
    # lines stay present everywhere but are strongest in the atmospheric centre
    line_amt = 0.45 + 0.55 * m
    gain = (1 + cfg["depth"] * m)
    gain *= 1 - cfg["line_dark"] * dark * line_amt
    gain *= 1 + cfg["line_light"] * light * line_amt
    return gain


def background_weight(rgb, style):
    """Soft 0..1 mask of pixels that are the post background (connected to the
    canvas edge and matching the background colour), so photos, frames,
    embroidery and type are left untouched."""
    a = rgb.astype(np.float64)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    ref = {"beige": (253, 239, 212), "navy": (0, 48, 72)}[style]
    c1, c2, lum = r - b, g - b, (r + g + b) / 3
    rc1, rc2, rl = ref[0] - ref[2], ref[1] - ref[2], sum(ref) / 3
    dist = np.sqrt(4 * ((c1 - rc1) ** 2 + (c2 - rc2) ** 2) + 0.25 * (lum - rl) ** 2)
    soft = 1 - smoothstep(30, 50, dist)

    # keep only regions connected to the outside of the canvas
    cand = Image.fromarray(((soft > 0.5) * 255).astype(np.uint8))
    padded = Image.new("L", (cand.width + 2, cand.height + 2), 255)
    padded.paste(cand, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    conn = (np.asarray(padded)[1:-1, 1:-1] == 128)
    conn_img = Image.fromarray((conn * 255).astype(np.uint8))
    conn_img = conn_img.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    return soft * (np.asarray(conn_img) / 255.0)


def apply(rgb, style):
    h, w = rgb.shape[:2]
    gain = gain_map(w, h, style)
    wgt = background_weight(rgb, style)
    eff = 1 + (gain - 1) * wgt
    out = rgb.astype(np.float64) * eff[..., None]
    # tiny dither on treated pixels only, so the soft gradient never bands
    rng = np.random.default_rng(4)
    out += (rng.random(out.shape) - 0.5) * (np.abs(eff - 1) > 1e-4)[..., None]
    return np.clip(out, 0, 255).round().astype(np.uint8)


def export_layers(style, name, w=1080, h=1350):
    """Editable layers at full post size. Place them directly above the
    background layer (below photos and type) in the source file:
      *_depth_multiply.png     blend: Multiply     (beige: soft centre shadow)
      *_depth_colordodge.png   blend: Color Dodge  (navy: soft centre glow)
      *_lines_multiply.png     blend: Multiply     (thin dark line cores)
      *_lines_colordodge.png   blend: Color Dodge  (faint line highlights)
    Multiply by grey v gives gain v/255; Color Dodge by grey v gives gain
    1/(1-v/255). Both scale brightness only, so hue never shifts."""
    cfg = SETTINGS[style]
    m = center_mask(w, h)
    dark, light = line_profiles(w, h)
    amt = 0.45 + 0.55 * m
    d = OUT / "layers_1080x1350"

    def save_mult(gain, fname):
        Image.fromarray(np.clip(gain * 255, 0, 255).round().astype(np.uint8)).save(d / fname)

    def save_dodge(gain, fname):
        Image.fromarray(np.clip((1 - 1 / gain) * 255, 0, 255).round().astype(np.uint8)).save(d / fname)

    depth_gain = 1 + cfg["depth"] * m
    if cfg["depth"] < 0:
        save_mult(depth_gain, f"{name}_depth_multiply.png")
    else:
        save_dodge(depth_gain, f"{name}_depth_colordodge.png")
    save_mult(1 - cfg["line_dark"] * dark * amt, f"{name}_lines_multiply.png")
    save_dodge(1 + cfg["line_light"] * light * amt, f"{name}_lines_colordodge.png")


def main():
    grid = np.asarray(Image.open(SRC_GRID).convert("RGB"))
    out = grid.copy()
    for name, (x0, x1) in PANELS.items():
        style = POST_STYLE[name]
        panel = apply(grid[:, x0:x1], style)      # effect restarts per post
        out[:, x0:x1] = panel
        Image.fromarray(panel).save(OUT / "posts" / f"{name}_background.png")
        export_layers(style, name)
    Image.fromarray(out).save(OUT / "grid" / "grid_preview_background.png")

    # side-by-side before/after for review
    h, w = grid.shape[:2]
    cmp_img = Image.new("RGB", (w, h * 2 + 20), (255, 255, 255))
    cmp_img.paste(Image.fromarray(grid), (0, 0))
    cmp_img.paste(Image.fromarray(out), (0, h + 20))
    cmp_img.save(OUT / "grid" / "grid_before_after.jpg", quality=92)


if __name__ == "__main__":
    main()
