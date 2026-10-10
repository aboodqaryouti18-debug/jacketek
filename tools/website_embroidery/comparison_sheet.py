"""Close-up comparison: the real website's embroidery vs the three post words.
Usage: python3 tools/website_embroidery/comparison_sheet.py
"""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "work" / "website_embroidery"
OUT = ROOT / "export" / "website_embroidery"
SHEET_W = 2400
CROPS = {"POST_04": (140, 730, 480, 840), "POST_05": (290, 155, 520, 235), "POST_06": (360, 755, 525, 840)}
WORDS = {"POST_04": "dhikrayatak", "POST_05": "tafseela", "POST_06": "ma'na"}


def label(img, text, h=56):
    pad = np.full((h, img.shape[1], 3), 255, np.uint8)
    cv2.putText(pad, text, (12, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (40, 40, 40), 2, cv2.LINE_AA)
    return np.vstack([pad, img])


def fit_h(img, h):
    return cv2.resize(img, (round(img.shape[1] * h / img.shape[0]), h), interpolation=cv2.INTER_AREA if img.shape[0] > h else cv2.INTER_LANCZOS4)


def row(*panels, gap=24):
    h = max(p.shape[0] for p in panels)
    parts = []
    for p in panels:
        q = np.full((h, p.shape[1], 3), 255, np.uint8)
        q[:p.shape[0]] = p
        parts += [q, np.full((h, gap, 3), 255, np.uint8)]
    r = np.hstack(parts[:-1])
    out = np.full((r.shape[0], SHEET_W, 3), 255, np.uint8)
    out[:, :min(SHEET_W, r.shape[1])] = r[:, :SHEET_W]
    return out


def detail(name, bg):
    """The 6x render (thread dyed crimson + its shadow) on the post's flat background colour."""
    t = cv2.imread(str(W / "render" / name / "render_thread.png"), cv2.IMREAD_UNCHANGED).astype(np.float64) / 255
    s = cv2.imread(str(W / "render" / name / "render_shadow.png"), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float64) / 255
    lum = t[..., :3] @ np.array([0.0722, 0.7152, 0.2126])  # BGR
    solid = cv2.erode((t[..., 3] > 0.99).astype(np.uint8), np.ones((9, 9))) > 0
    dyed = np.clip(lum[..., None] * np.array([0x1F, 0x12, 0xC1]) / 255 / lum[solid].mean(), 0, 1)
    base = np.array(bg[::-1], np.float64)[None, None] / 255 * (1 - s[..., None])
    a = t[..., 3:]
    return (np.clip(dyed * a + base * (1 - a), 0, 1) * 255).astype(np.uint8)


rows = []
site = []
for body in ("NavyBlue", "Beige"):
    im = cv2.imread(str(W / "site_capture" / f"closeup_{body}.png"))
    site.append(label(fit_h(im[700:1080, 500:1540], 380), f"WEBSITE (live configurator, Red thread, Lalezar) - {body} body"))
rows.append(row(*site))
for name, bgc in (("POST_04", (253, 239, 212)), ("POST_05", (0, 48, 72)), ("POST_06", (253, 239, 212))):
    x0, y0, x1, y1 = CROPS[name]
    before = cv2.imread(str(ROOT / "export" / "posts" / f"{name}_background.png"))[y0:y1, x0:x1]
    after = cv2.imread(str(OUT / f"{name}_website_embroidery.png"))[y0:y1, x0:x1]
    z = 330 / before.shape[0]
    rows.append(row(label(cv2.resize(before, None, fx=z, fy=z, interpolation=cv2.INTER_LANCZOS4), f"{name} before (x{z:.1f})"),
                    label(cv2.resize(after, None, fx=z, fy=z, interpolation=cv2.INTER_LANCZOS4), f"{name} after, in the post (x{z:.1f})")))
    rows.append(row(label(fit_h(detail(name, bgc), 420), f"{name} website pipeline render, 6x detail, flat background (preview of thread structure)")))
sheet = np.vstack([np.vstack([r, np.full((28, SHEET_W, 3), 255, np.uint8)]) for r in rows])
cv2.imwrite(str(OUT / "comparison_website_vs_posts.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 92])
print(sheet.shape)
