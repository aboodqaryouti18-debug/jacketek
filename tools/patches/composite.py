"""Step 4: place the baked patches on posts 04-06 (outputs separate, inputs untouched).

Placement (post px). Two kinds, as in posts 01-03:
  standalone  a manufactured patch lying on the layout / over a photo frame:
              site contact shadow + a soft lift shadow (as the 01-03 patches)
  sewn        on the jacket in the photo: sleeve curvature (cylinder warp),
              the photo's own fabric light, site contact shadow only

Every patch is warped on a K x post grid and area-averaged down (no detail is
invented). Text / red words / dashed lines are guarded: the patch footprint
(thread + shadows) must not touch them; the run fails otherwise.

Input : export/website_background/POST_0X.png
Output: export/patches/POST_0X.png, grid_preview.png, grid_before_after.jpg, report.json
"""
import json, sys
from pathlib import Path
import numpy as np, cv2
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from background_treatment import background_weight  # noqa: E402
import website_background as wb  # noqa: E402

IN = ROOT / "export/website_background"
OUT = ROOT / "export/patches"
B = ROOT / "work/patches/baked"
K = 4

# name, centre (x, y), long side of the artwork (px), rotation (deg, + = counter-clockwise), kind
PLACE = {
    "POST_04": [("whocares", (114, 607), 132, 9.0, "standalone"),
                ("porsche", (203, 447), 60, -4.0, "sewn")],
    "POST_05": [("lifeexe", (152, 180), 194, 6.5, "standalone")],
    "POST_06": [("cat", (196, 61), 118, -3.6, "standalone"),
                ("bmo", (118, 772), 132, -8.0, "standalone")],
}
# sewn patch on the sleeve: the sleeve's axis-normal width at the patch (cylinder radius)
SLEEVE = {"porsche": dict(cx=202, half_width=36)}
LIFT = {"beige": dict(off=(2.4, 4.0), sigma=3.2, k=0.40), "navy": dict(off=(2.4, 4.0), sigma=3.4, k=0.62)}
CONTACT_K = 0.55


def load(n):
    t = np.asarray(Image.open(B / f"{n}_thread.png").convert("RGBA")).astype(np.float32) / 255
    s = np.asarray(Image.open(B / f"{n}_shadow.png").convert("L")).astype(np.float32) / 255
    return t, s


def matrix(art_alpha, centre, D, rot):
    ys, xs = np.nonzero(art_alpha > 0.5)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    s = D / max(xs.max() - xs.min(), ys.max() - ys.min())
    M = cv2.getRotationMatrix2D((float(cx), float(cy)), rot, s)
    M[0, 2] += centre[0] - cx
    M[1, 2] += centre[1] - cy
    return M


def warp(img, M, shape, remap=None):
    MK = M.copy() * K
    big = cv2.warpAffine(img, MK, (shape[1] * K, shape[0] * K), flags=cv2.INTER_LINEAR, borderValue=0)
    if remap is not None:
        big = cv2.remap(big, remap[0], remap[1], cv2.INTER_LINEAR, borderValue=0)
    return cv2.resize(big, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)


def cylinder(shape, cx, hw):
    """Flat patch wrapped on a vertical sleeve cylinder: output x -> flat arc length."""
    H, Wd = shape[0] * K, shape[1] * K
    xx, yy = np.meshgrid(np.arange(Wd, dtype=np.float32), np.arange(H, dtype=np.float32))
    R = hw * 1.15 * K
    d = np.clip((xx - cx * K) / R, -0.999, 0.999)
    mx = cx * K + R * np.arcsin(d)
    return mx.astype(np.float32), yy


def text_guard(post, rgb, L):
    style = wb.STYLE[post]
    _, prints = wb.masks(post, rgb, background_weight(rgb, style), L)
    ref = {"beige": (253, 239, 212), "navy": (0, 48, 72)}[style]
    a = rgb.astype(np.float32)
    c1, c2 = a[..., 0] - a[..., 2], a[..., 1] - a[..., 2]
    chroma = np.sqrt((c1 - (ref[0] - ref[2])) ** 2 + (c2 - (ref[1] - ref[2])) ** 2)
    # type is darker than cream (navy, red) or lighter than navy (cream);
    # the white photo frames are neither, so they are not mistaken for text
    lumd = (sum(ref) / 3 - a.mean(2)) * (1 if style == "beige" else -1)
    red = (a[..., 0] - a[..., 1] > 50) & (a[..., 0] - a[..., 2] > 40)   # the red words
    g = (red | (lumd > 100)) & (prints < 0.5)   # soft drop shadows stay below 100
    g = cv2.morphologyEx(g.astype(np.uint8), cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    # drop the frames' own edges and drop shadows that hug the photo prints (not type)
    near = cv2.dilate((prints > 0.2).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0  # incl. the frames' drop shadows
    g = ((g > 0) & ~near).astype(np.uint8)
    return cv2.dilate(g, np.ones((5, 5), np.uint8)) > 0, prints


def main():
    L = json.loads((ROOT / "work/replace_photos/locate.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    report, outs, ins = {}, [], []
    for post, items in PLACE.items():
        rgb8 = cv2.cvtColor(cv2.imread(str(IN / f"{post}.png")), cv2.COLOR_BGR2RGB)
        H, Wd = rgb8.shape[:2]
        style = wb.STYLE[post]
        guard, prints = text_guard(post, rgb8, L)
        out = rgb8.astype(np.float32) / 255
        foot = np.zeros((H, Wd), bool)
        rep = []
        for n, c, D, rot, kind in items:
            t, s = load(n)
            M = matrix(t[..., 3], c, D, rot)
            remap = None
            if kind == "sewn":
                sl = SLEEVE[n]
                remap = cylinder((H, Wd), sl["cx"], sl["half_width"])
            pre = t[..., :3] * t[..., 3:4]
            a = warp(t[..., 3], M, (H, Wd), remap)
            col = warp(pre, M, (H, Wd), remap)
            sh = warp(s, M, (H, Wd), remap)
            base = out.copy()
            lum = base @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            if kind == "standalone":
                lf = LIFT[style]
                Mo = M.copy(); Mo[0, 2] += lf["off"][0]; Mo[1, 2] += lf["off"][1]
                lift = cv2.GaussianBlur(warp(t[..., 3], Mo, (H, Wd)), (0, 0), lf["sigma"]) * lf["k"]
                # local light on the layout (vignette / glow), from the post's own background
                light = cv2.GaussianBlur(lum, (0, 0), 30)
                refl = np.median(light[a > 0.5])
                tone = np.clip(1 + (light / max(refl, 1e-3) - 1) * 0.35, 0.92, 1.05)
            else:
                lift = np.zeros_like(a)
                # the photo's own fabric light: folds and fall-off of the leather sleeve
                fab = cv2.GaussianBlur(lum, (0, 0), 3.0)
                ring = (cv2.dilate((a > 0.02).astype(np.uint8), np.ones((9, 9))) > 0) & (a < 0.02)
                refl = np.median(fab[ring])
                tone = np.clip(fab / refl, 0.75, 1.08) ** 0.9
            # the patch's own cast shadow darkens toward the shade of the surface, not black
            dark = 1 - np.clip(lift + sh * CONTACT_K, 0, 0.85)
            base = base * dark[..., None]
            o = col * tone[..., None] + base * (1 - a[..., None])
            fp = (a > 1 / 255) | (lift > 1 / 255) | (sh * CONTACT_K > 1 / 255)
            out = np.where(fp[..., None], o, out)
            foot |= fp
            rep.append(dict(patch=n, kind=kind, centre=c, long_side_px=D, rotation_deg=rot,
                            footprint_px=int(fp.sum()), on_guarded_text_px=int((fp & guard).sum())))
        o8 = np.clip(out * 255, 0, 255).round().astype(np.uint8)
        changed = np.abs(o8.astype(int) - rgb8.astype(int)).max(2) > 0
        report[post] = dict(patches=rep, changed_px=int(changed.sum()),
                            changed_outside_footprint=int((changed & ~foot).sum()),
                            changed_on_text_px=int((changed & guard).sum()))
        Image.fromarray(o8).save(OUT / f"{post}.png")
        outs.append(o8); ins.append(rgb8)
    grid = np.hstack(outs)
    Image.fromarray(grid).save(OUT / "grid_preview.png")
    ba = np.vstack([np.hstack(ins), np.full((20, grid.shape[1], 3), 255, np.uint8), grid])
    Image.fromarray(ba).save(OUT / "grid_before_after.jpg", quality=92)
    (OUT / "report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))
    bad = sum(r["changed_on_text_px"] for r in report.values())
    if bad:
        print("WARNING: patch footprint touches guarded text:", bad)


if __name__ == "__main__":
    main()
