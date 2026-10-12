"""Start frames for the JACKETEK "continuous thread" ad (warm beige world).

Jacket pixels are the original photos; only the background is new.
Outputs 1080x1920 PNGs in work/ad/frames/.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
REFS = ROOT / "source/video_refs"
CUT = ROOT / "work/reel/cutouts"
OUT = ROOT / "work/ad/frames"
W, H = 1080, 1920

BEIGE = np.array([0xFD, 0xF0, 0xD5], float)        # brand warm beige
BEIGE_EDGE = np.array([0xEE, 0xDC, 0xB8], float)   # same hue, a little deeper


def beige_bg(cx=0.5, cy=0.45):
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx / W - cx) / 0.8) ** 2 + ((yy / H - cy) / 0.95) ** 2)
    t = np.clip(d, 0, 1)[..., None] ** 1.8
    img = BEIGE * (1 - t) + BEIGE_EDGE * t
    img += np.random.default_rng(3).normal(0, 0.8, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")


def front_on_beige(width, cy):
    cut = Image.open(CUT / "jk_front_cut.png")
    cut = cut.crop(cut.getbbox())
    s = width / cut.width
    cut = cut.resize((round(cut.width * s), round(cut.height * s)), Image.LANCZOS)
    x, y = (W - cut.width) // 2, round(cy * H - cut.height / 2)
    bg = beige_bg()
    a = np.array(cut)[..., 3].astype(float) / 255
    layer = Image.new("RGBA", cut.size, (90, 40, 30, 0))
    layer.putalpha(Image.fromarray((a * 60).astype(np.uint8)))
    sh = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    sh.alpha_composite(layer, (x + 6, y + 30))
    bg.alpha_composite(sh.filter(ImageFilter.GaussianBlur(40)))
    bg.alpha_composite(cut, (x, y))
    return bg.convert("RGB"), (x, y, s)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    full, geo = front_on_beige(940, 0.47)
    full.save(OUT / "front_beige.png")
    (OUT / "front_beige_geo.txt").write_text("%d %d %.6f\n" % geo)

    # close crop of the same composition (chest + collar), for a pull-back
    # that ends exactly on front_beige.png
    z = 2.0
    big = full.resize((W * 2, H * 2), Image.LANCZOS)
    cx, cy = W * z * 0.5, H * z * 0.36
    big.crop((int(cx - W / 2), int(cy - H / 2), int(cx + W / 2), int(cy + H / 2))).save(OUT / "front_close.png")

    # 09 sleeve (1185x2000) -> 9:16 crop, 09 kept in frame
    s09 = Image.open(ROOT / "source/new_photos_l/09_l.webp").convert("RGB")
    cw = round(s09.height * W / H)
    x0 = min(max(0, 380 - cw // 2 + 120), s09.width - cw)
    s09.crop((x0, 0, x0 + cw, s09.height)).resize((W, H), Image.LANCZOS).save(OUT / "sleeve09.png")


if __name__ == "__main__":
    main()
