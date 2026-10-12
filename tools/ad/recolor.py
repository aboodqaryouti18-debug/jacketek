"""Recoloured variants of the front jacket for the customisation scene.

Only the chosen panel changes:
  sleeves  = the cream leather sleeves + the two pocket welts (the welts take
             the sleeve material, see jacketportable orderToProductionOrder.ts)
  body     = the burgundy wool body panels
Trims (striped collar, cuffs, waistband), lettering, patches and snaps are
never touched. Colours are real configurator options from
jacketportable/src/features/configurator/model/catalog.ts.

Output (work/ad/recolor/, all 2000x2000 RGBA, same geometry as the cut-out):
  front_orig.png, front_sleeves.png (sleeves Black), front_sleeves_body.png
  (sleeves Black + body Royal Blue), mask_sleeves.png, mask_body.png
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "work/ad/recolor"

SLEEVE_TARGET = "#111111"   # Black leather
BODY_TARGET = "#17479E"     # Royal Blue felt

# Trim zones in source px (2000x2000 front photo)
COLLAR = [(830, 90), (1240, 90), (1250, 200), (1130, 390), (1000, 410), (870, 390), (820, 200)]
CUFF_Y = 1680    # cuff tops (sleeves)


def hexrgb(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], float)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cut = np.array(Image.open(ROOT / "work/reel/cutouts/jk_front_cut.png").convert("RGBA")).astype(float)
    rgb, a = cut[..., :3], cut[..., 3] / 255
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = (mx - mn) / np.maximum(mx, 1)
    lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255

    zone = Image.new("L", (2000, 2000), 255)
    ImageDraw.Draw(zone).polygon(COLLAR, fill=0)
    zone = np.array(zone) > 0
    yy, xx = np.mgrid[0:2000, 0:2000]

    # leather = unsaturated and not dark; flood-filled from a seed inside each
    # sleeve and each welt, so snaps, lettering and patches (separate islands
    # surrounded by burgundy) are never reached.
    leather = (sat < 0.30) & (lum > 0.28) & (a > 0.5) & zone & (yy < CUFF_Y)
    seeds = [(300, 1000), (1700, 1000), (300, 600), (1700, 600), (600, 1400), (1470, 1400)]
    labels, _ = ndimage.label(leather)
    keep = {labels[sy, sx] for sx, sy in seeds} - {0}
    sleeves = np.isin(labels, list(keep))

    # body bottom = the waistband rib seam (slants down toward the placket;
    # the felt placket itself runs to the hem)
    seam_x = [0, 380, 560, 900, 902, 1170, 1172, 1400, 1640, 2000]
    seam_y = [1665, 1665, 1690, 1738, 1915, 1915, 1740, 1707, 1665, 1665]
    ybot = np.interp(xx, seam_x, seam_y)
    burg = (r > g * 1.35) & (r > b * 1.2) & (sat > 0.30) & (lum < 0.45)
    body = burg & zone & (yy < ybot) & (a > 0.5) & (xx > 340) & (xx < 1680)

    def soft(m):
        im = Image.fromarray((m * 255).astype(np.uint8))
        im = im.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
        return np.array(im).astype(float) / 255

    ms, mb = soft(sleeves), soft(body)

    def recolour(src, mask, target, k):
        lmed = np.median(lum[mask > 0.9])
        t = hexrgb(target)
        new = t[None, None, :] + k * (lum - lmed)[..., None] * 255
        new = np.clip(new, 0, 255)
        m = mask[..., None]
        return src * (1 - m) + new * m

    orig = rgb.copy()
    s1 = recolour(orig, ms, SLEEVE_TARGET, 0.55)
    s2 = recolour(s1, mb, BODY_TARGET, 1.15)
    alpha = cut[..., 3:4]
    for name, arr in (("front_orig", orig), ("front_sleeves", s1), ("front_sleeves_body", s2)):
        Image.fromarray(np.concatenate([arr, alpha], -1).astype(np.uint8), "RGBA").save(OUT / f"{name}.png")
    Image.fromarray((ms * 255).astype(np.uint8)).save(OUT / "mask_sleeves.png")
    Image.fromarray((mb * 255).astype(np.uint8)).save(OUT / "mask_body.png")


if __name__ == "__main__":
    main()
