"""Build the 9:16 start frames for the JACKETEK reel from the original photos.

The jacket pixels are the supplied photos; only the background is new
(pale ice-blue studio sweep) and the crops/scales are chosen per shot.

Inputs : source/video_refs/*.webp, and the BiRefNet cut-outs
         work/reel/cutouts/jk_front_cut.png, jk_back_cut.png
Outputs: work/reel/frames/*.png (1080x1920)
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "source/video_refs"
CUT = ROOT / "work/reel/cutouts"
OUT = ROOT / "work/reel/frames"
W, H = 1080, 1920

# Pale cyan / ice blue, lighter in the centre, a touch deeper at the edges.
ICE_CENTRE = np.array([231, 246, 249], float)
ICE_EDGE = np.array([196, 226, 234], float)


def ice_background(cx=0.5, cy=0.45, tint=(0, 0, 0)):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx / W - cx) / 0.75) ** 2 + ((yy / H - cy) / 0.9) ** 2)
    t = np.clip(d, 0, 1)[..., None] ** 1.6
    img = ICE_CENTRE * (1 - t) + ICE_EDGE * t + np.array(tint, float)
    # very fine grain so the gradient does not band after video encoding
    img += np.random.default_rng(7).normal(0, 0.8, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def place_cutout(bg, cut, width, cy):
    cut = cut.crop(cut.getbbox())
    s = width / cut.width
    cut = cut.resize((round(cut.width * s), round(cut.height * s)), Image.LANCZOS)
    x = (W - cut.width) // 2
    y = round(cy * H - cut.height / 2)
    # soft contact shadow, slightly below and behind the garment
    a = np.array(cut)[..., 3].astype(float) / 255
    sh = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    shadow = Image.fromarray((a * 70).astype(np.uint8))
    layer = Image.new("RGBA", cut.size, (40, 70, 80, 0))
    layer.putalpha(shadow)
    sh.alpha_composite(layer, (x + 6, y + 28))
    sh = sh.filter(ImageFilter.GaussianBlur(38))
    bg.alpha_composite(sh)
    bg.alpha_composite(cut, (x, y))
    return bg


def crop_fill(img, cx, cy, scale):
    """Scale img and crop a WxH window centred on (cx, cy) in source px.
    Missing rows at the bottom are filled by ping-ponging the plain fabric
    strip along the bottom edge (the lowest 120 px), so no lettering or
    patch is ever mirrored into the frame."""
    im = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    a = np.array(im.convert("RGB"))
    if a.shape[0] < H:
        pad = H - a.shape[0]
        strip = a[-120:]
        tiles, flip = [], True
        while sum(t.shape[0] for t in tiles) < pad:
            tiles.append(strip[::-1] if flip else strip)
            flip = not flip
        a = np.concatenate([a] + tiles, axis=0)[:a.shape[0] + pad]
    x0 = int(np.clip(round(cx * scale - W / 2), 0, a.shape[1] - W))
    y0 = int(np.clip(round(cy * scale - H / 2), 0, a.shape[0] - H))
    return Image.fromarray(a[y0:y0 + H, x0:x0 + W])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    front = Image.open(CUT / "jk_front_cut.png")
    back = Image.open(REFS / "jk_back.webp")

    # S1 the idea: medium-wide front on ice blue
    place_cutout(ice_background(), front, 940, 0.47).convert("RGB").save(OUT / "s1_front.png")
    # S4 hero: a little smaller, more air above, cooler sweep
    place_cutout(ice_background(cy=0.4, tint=(-3, 0, 2)), front, 860, 0.48).convert("RGB").save(OUT / "s4_hero.png")

    # S2 details (garment fills the frame)
    chest = Image.open(REFS / "jk_chest.webp")              # 2000x857: chest lettering + collar
    crop_fill(chest, 470, 440, 1.75).save(OUT / "s2_chest.png")
    sleeve = Image.open(REFS / "jk_sleeve.webp")            # 1483x2000: sleeve + patch
    crop_fill(sleeve, 960, 1000, H / sleeve.height).save(OUT / "s2_sleeve.png")

    # S3 embroidery: the JK patch, then a macro of the K satin border
    patch = Image.open(REFS / "jk_patch.webp")              # 2000x1778
    crop_fill(patch, 1380, 889, H / patch.height).save(OUT / "s3_patch.png")
    crop_fill(patch, 1120, 1050, 2.4).save(OUT / "s3_macro.png")

    # S4 back: SENIOR 2027 fills the frame
    crop_fill(back, 770, 600, 1.38).save(OUT / "s4_back.png")


if __name__ == "__main__":
    main()
