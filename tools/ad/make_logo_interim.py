"""INTERIM logo for the finale, rebuilt from the website's own Wordmark
(jacketportable/src/components/Wordmark.tsx): a varsity "J" woven tag
(Graduate font) with a dashed stitched edge, beside the letter-spaced
JACKETEK wordmark. Replace with the official logo file via --logo.

Output: work/ad/logo/logo_interim.png (transparent)
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = Path("/home/user/jacketportable/public/fonts/embroidery")
INK = (100, 21, 43)          # burgundy ink on the beige world
INK_INV = (253, 240, 213)
STITCH = (193, 18, 31)       # crimson stitch
K = 12                       # render scale (site: tag 24x30, wordmark 18px)


def main():
    out = ROOT / "work/ad/logo"
    out.mkdir(parents=True, exist_ok=True)
    tag_w, tag_h, gap = 24 * K, 30 * K, 12 * K
    word_font = ImageFont.truetype(str(FONTS / "montserrat.ttf"), 18 * K)
    j_font = ImageFont.truetype(str(FONTS / "graduate.ttf"), 15 * K)
    spacing = 0.36 * 18 * K
    letters = "JACKETEK"
    widths = [word_font.getlength(c) for c in letters]
    word_w = sum(widths) + spacing * (len(letters) - 1)
    W = int(tag_w + gap + word_w + 4 * K)
    H = int(tag_h + 4 * K)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    y0 = 2 * K
    d.rectangle((0, y0, tag_w, y0 + tag_h), fill=INK + (255,))
    d.text((tag_w / 2, y0 + tag_h / 2), "J", font=j_font, fill=INK_INV + (255,), anchor="mm")
    # 1px dashed outline, offset -4px (inside the tag), crimson
    o, dash = 4 * K, 3 * K
    x0, x1, ya, yb = o, tag_w - o, y0 + o, y0 + tag_h - o
    for x in range(int(x0), int(x1), 2 * dash):
        d.line((x, ya, min(x + dash, x1), ya), fill=STITCH + (255,), width=K)
        d.line((x, yb, min(x + dash, x1), yb), fill=STITCH + (255,), width=K)
    for y in range(int(ya), int(yb), 2 * dash):
        d.line((x0, y, x0, min(y + dash, yb)), fill=STITCH + (255,), width=K)
        d.line((x1, y, x1, min(y + dash, yb)), fill=STITCH + (255,), width=K)
    x = tag_w + gap
    for c, w in zip(letters, widths):
        d.text((x, y0 + tag_h / 2), c, font=word_font, fill=INK + (255,), anchor="lm", stroke_width=int(K * 0.35),
               stroke_fill=INK + (255,))
        x += w + spacing
    im.save(out / "logo_interim.png")


if __name__ == "__main__":
    main()
