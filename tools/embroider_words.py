"""JACKETEK posts 04-06: raised red-thread embroidery on three red words.

  POST 04  «ذكرياتك»   POST 05  «تفصيلة»   POST 06  «معنى»

Works on the existing flattened exports (export/posts/POST_0X_background.png),
the highest-resolution versions of these posts that exist. Only the pixels of
the three words (and the soft shadow they cast) are changed.

Pipeline per word
  1. Mask: the red letter components are picked by colour inside a word box,
     then a soft (anti-aliased) alpha is recovered by unmixing each edge pixel
     between the brand red and the locally inpainted background.
  2. The mask is rendered at RENDER_SCALE x for stitch detail:
       - stitch direction = across the stroke (normal from the distance
         transform), smoothed and slanted like satin stitch,
       - thread texture = line-integral convolution of fine noise along that
         direction, so every thread follows the letter's stroke,
       - raised "pillow" height from the distance transform -> lighting,
         darker rolled edges, slightly frayed thread ends.
  3. Downsampled back, colour-normalised so the average stays the existing
     red, and composited with a soft contact/drop shadow.

Intermediate masks and renders go to work/embroidery/ for later adjustment.

Usage:  python3 tools/embroider_words.py
Needs:  numpy, opencv-python-headless, Pillow
"""
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "export" / "posts"
WORK = ROOT / "work" / "embroidery"
GRID = ROOT / "export" / "grid"

RED = np.array([193, 18.6, 32.2], np.float64)   # existing brand red (measured inside the letters)
RENDER_SCALE = 4

# Word boxes (x0, y0, x1, y1) in post pixels. They exclude the red full stops
# (kept flat, as in the reference) and every other red element in the posts.
WORDS = {
    "POST_04": dict(word="ذكرياتك", box=(170, 736, 472, 834), bg="beige"),
    "POST_05": dict(word="تفصيلة", box=(312, 160, 510, 230), bg="navy"),
    "POST_06": dict(word="معنى", box=(366, 762, 518, 832), bg="beige"),
}

# Look settings
STITCH_SLANT_DEG = 10      # satin-stitch slant relative to the stroke normal
THREAD_PITCH = 1.3         # post px between neighbouring threads
RIDGE_MIX = 0.6            # regular satin ridges vs. random thread variation
DOT_AREA = 260             # parts smaller than this (post px^2) count as dots
DOT_STITCH_DEG = 75        # fixed stitch angle for dots (image coords)
THREAD_CONTRAST = 0.20     # strength of individual thread highlights/shadows
RELIEF = 0.24              # strength of the raised pillow lighting
EDGE_DARKEN = 0.18         # threads rolling under at the edges
FRAY = 0.20                # thread-end roughness on the outline (alpha)
SHADOW = {"beige": 0.30, "navy": 0.55}   # drop-shadow darkening
SHADOW_OFFSET = (1.2, 1.8)               # px (x, y) in post pixels
SHADOW_BLUR = 1.6


def red_mask(img, box):
    """Hard mask of red components inside the word box."""
    x0, y0, x1, y1 = box
    a = img.astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    red = ((r > 120) & (r - g > 60) & (r - b > 45)).astype(np.uint8)
    inbox = np.zeros_like(red)
    inbox[y0:y1, x0:x1] = 1
    red &= inbox
    k, lab, st, _ = cv2.connectedComponentsWithStats(red, connectivity=8)
    keep = np.zeros_like(red)
    for i in range(1, k):
        if st[i, cv2.CC_STAT_AREA] >= 6:
            keep[lab == i] = 1
    return keep


def soft_alpha(img, hard):
    """Recover anti-aliased coverage by unmixing red vs. inpainted background."""
    grow = cv2.dilate(hard, np.ones((5, 5), np.uint8))
    bg = cv2.inpaint(img, grow * 255, 4, cv2.INPAINT_TELEA).astype(np.float64)
    p = img.astype(np.float64)
    d = RED[None, None, :] - bg
    alpha = ((p - bg) * d).sum(2) / np.maximum((d * d).sum(2), 1.0)
    alpha = np.clip(alpha, 0, 1) * cv2.dilate(hard, np.ones((3, 3), np.uint8))
    alpha[hard.astype(bool) & (alpha > 0.85)] = 1.0
    return alpha, bg


def smooth_orientation(gx, gy, sigma):
    """Average an axial (sign-free) direction field with the double-angle trick."""
    th = np.arctan2(gy, gx)
    w = np.hypot(gx, gy)
    c = cv2.GaussianBlur(w * np.cos(2 * th), (0, 0), sigma)
    s = cv2.GaussianBlur(w * np.sin(2 * th), (0, 0), sigma)
    return 0.5 * np.arctan2(s, c)


def lic(noise, theta, length, step=0.75):
    """Average noise along a straight segment at each pixel's stitch angle.
    Straight segments (not streamlines) keep satin threads straight."""
    h, w = noise.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = np.cos(theta).astype(np.float32)
    dy = np.sin(theta).astype(np.float32)
    acc = noise.astype(np.float32).copy()
    wsum = np.ones_like(acc)
    n = int(length / step)
    for i in range(1, n + 1):
        t = np.float32(i * step)
        wgt = np.float32(1 - i / (n + 1)) ** 0.5
        for sign in (1, -1):
            acc += wgt * cv2.remap(noise, xx + sign * t * dx, yy + sign * t * dy,
                                   cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            wsum += wgt
    return acc / wsum


def render_embroidery(alpha, seed):
    """Return (shade factor, alpha) at RENDER_SCALE for a word crop."""
    S = RENDER_SCALE
    h, w = alpha.shape
    big = cv2.resize(alpha, (w * S, h * S), interpolation=cv2.INTER_CUBIC)
    # crisp, original shape at high res (smoothstep around 50% coverage)
    t = np.clip((big - 0.35) / 0.3, 0, 1)
    big_a = t * t * (3 - 2 * t)
    hard = (big_a > 0.5).astype(np.uint8)

    dist = cv2.distanceTransform(hard, cv2.DIST_L2, 5).astype(np.float64)
    dsm = cv2.GaussianBlur(dist, (0, 0), 1.2 * S)
    gy, gx = np.gradient(dsm)
    normal = smooth_orientation(gx, gy, 5.0 * S)
    theta = normal + np.deg2rad(STITCH_SLANT_DEG)
    # small detached parts (Arabic dots, diamonds) have no dominant stroke
    # direction: stitch them in one straight diagonal run, like the reference
    k, lab, st, _ = cv2.connectedComponentsWithStats(hard, connectivity=8)
    for i in range(1, k):
        if st[i, cv2.CC_STAT_AREA] < DOT_AREA * S * S:
            theta[lab == i] = np.deg2rad(DOT_STITCH_DEG)
    theta = theta.astype(np.float32)

    rng = np.random.default_rng(seed)
    noise = rng.standard_normal((h * S, w * S)).astype(np.float32)
    # thread width ~1.3 post px; long runs so each thread spans the stroke
    noise = cv2.GaussianBlur(noise, (0, 0), 0.7)
    threads = lic(noise, theta, length=4 * S)
    threads = (threads - threads.mean()) / (threads.std() + 1e-6)
    # regular satin ridges: one rounded thread every THREAD_PITCH post px,
    # running along the stitch direction, with a slight hand-made wobble
    yy, xx = np.mgrid[0:h * S, 0:w * S].astype(np.float32)
    wobble = cv2.GaussianBlur(rng.standard_normal((h * S, w * S)).astype(np.float32), (0, 0), 3 * S)
    wobble /= wobble.std() + 1e-6
    # straight stripes per 10-degree angle bin, softly blended by how close
    # each pixel's stitch angle is -> no moire where the direction turns
    th = np.mod(theta, np.pi)
    ridges = np.zeros_like(th)
    wsum = np.zeros_like(th)
    for b in np.deg2rad(np.arange(0, 180, 10)):
        diff = np.angle(np.exp(1j * 2 * (th - b))) / 2          # axial difference
        wgt = np.exp(-(diff / np.deg2rad(5)) ** 2).astype(np.float32)
        if wgt.max() < 1e-3:
            continue
        u = -xx * np.sin(b) + yy * np.cos(b)
        ridges += wgt * np.cos(2 * np.pi * u / (THREAD_PITCH * S) + 0.9 * wobble)
        wsum += wgt
    ridges /= np.maximum(wsum, 1e-6)
    threads = RIDGE_MIX * ridges + (1 - RIDGE_MIX) * threads
    threads /= threads.std() + 1e-6
    # a little coarser variation: neighbouring thread bundles differ in sheen
    bundles = lic(cv2.GaussianBlur(rng.standard_normal((h * S, w * S)).astype(np.float32), (0, 0), 2.5),
                  theta, length=3 * S)
    bundles = (bundles - bundles.mean()) / (bundles.std() + 1e-6)

    # raised pillow: height saturates a few px inside the edge
    height = 1 - np.exp(-dist / (2.6 * S))
    hgy, hgx = np.gradient(cv2.GaussianBlur(height, (0, 0), 0.8 * S) * 2.2 * S)
    nz = 1.0 / np.sqrt(hgx ** 2 + hgy ** 2 + 1)
    nx, ny = -hgx * nz, -hgy * nz
    light = np.array([-0.55, -0.65, 0.52])
    light /= np.linalg.norm(light)
    lam = nx * light[0] + ny * light[1] + nz * light[2]
    relief = 1 + RELIEF * (lam - light[2])

    # threads catch light more where they face it; edges roll under
    sheen = 1 + THREAD_CONTRAST * np.tanh(1.2 * threads) + 0.05 * bundles
    edge = 1 - EDGE_DARKEN * np.exp(-dist / (0.9 * S))
    shade = relief * sheen * edge

    # frayed thread ends along the outline only
    rim = np.exp(-dist / (1.0 * S)) * (big_a > 0)
    a_out = np.clip(big_a + FRAY * rim * np.tanh(threads), 0, 1) * (big_a > 0.02)
    return shade, a_out, theta, threads


def embroider_post(name):
    cfg = WORDS[name]
    src = POSTS / f"{name}_background.png"
    img = cv2.cvtColor(cv2.imread(str(src)), cv2.COLOR_BGR2RGB)
    hard = red_mask(img, cfg["box"])
    alpha, bg = soft_alpha(img, hard)

    ys, xs = np.nonzero(hard)
    pad = 8
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad + 1, img.shape[0])
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad + 1, img.shape[1])
    a_crop = alpha[y0:y1, x0:x1]

    shade, a_big, theta, threads = render_embroidery(a_crop, seed=sum(map(ord, name)))
    S = RENDER_SCALE
    hc, wc = a_crop.shape
    # premultiply before downsampling so outline pixels average correctly
    shade_small = cv2.resize(shade * a_big, (wc, hc), interpolation=cv2.INTER_AREA)
    a_small = cv2.resize(a_big, (wc, hc), interpolation=cv2.INTER_AREA)
    shade_small = shade_small / np.maximum(a_small, 1e-4)
    # keep the average colour on the existing red
    inner = a_small > 0.9
    shade_small /= np.average(shade_small[inner])

    # shade -> colour: darken by multiply, lift highlights gently toward a
    # lighter thread red (matte, not glossy)
    f = shade_small[..., None]
    lift = np.clip(f - 1, 0, None)
    emb = RED * np.minimum(f, 1) + lift * (np.array([236, 92, 98]) - RED) * 1.6
    # exact colour match: the mean of the stitched letters equals the original red
    emb += RED - emb[inner].mean(0)
    emb = np.clip(emb, 0, 255)

    # drop / contact shadow onto the background
    sh_src = cv2.resize(a_big, (wc, hc), interpolation=cv2.INTER_AREA)
    M = np.float32([[1, 0, SHADOW_OFFSET[0]], [0, 1, SHADOW_OFFSET[1]]])
    sh = cv2.warpAffine(sh_src, M, (wc, hc))
    sh = cv2.GaussianBlur(sh, (0, 0), SHADOW_BLUR)
    contact = cv2.GaussianBlur(sh_src, (0, 0), 0.8)
    shadow = np.clip(SHADOW[cfg["bg"]] * sh + 0.12 * contact, 0, 0.7)

    bg_crop = bg[y0:y1, x0:x1].copy()
    orig_crop = img[y0:y1, x0:x1].astype(np.float64)
    # outside the letters keep the ORIGINAL pixels (only shadowed)
    letter_zone = cv2.dilate(hard[y0:y1, x0:x1], np.ones((5, 5), np.uint8)).astype(bool)
    base = np.where(letter_zone[..., None], bg_crop, orig_crop)
    base = base * (1 - shadow[..., None])
    a3 = a_small[..., None]
    comp = a3 * emb + (1 - a3) * base
    # the shadow fades to zero; snap untouched pixels back exactly
    touched = (shadow > 0.004) | (a_small > 0.002) | letter_zone
    out_crop = np.where(touched[..., None], comp, orig_crop)

    out = img.copy()
    out[y0:y1, x0:x1] = np.clip(out_crop, 0, 255).round().astype(np.uint8)

    # intermediates for later adjustment
    WORK.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(WORK / f"{name}_mask_hard.png"), hard * 255)
    cv2.imwrite(str(WORK / f"{name}_mask_alpha.png"), (alpha * 255).round().astype(np.uint8))
    hsv = np.zeros(theta.shape + (3,), np.uint8)
    hsv[..., 0] = ((np.mod(theta, np.pi) / np.pi) * 179).astype(np.uint8)
    hsv[..., 1] = 255
    hsv[..., 2] = (a_big * 255).astype(np.uint8)
    cv2.imwrite(str(WORK / f"{name}_stitch_direction_x{S}.png"), cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR))
    # full-detail render of the word for close inspection
    f_big = shade[..., None] / np.average(shade[a_big > 0.9])
    lift_b = np.clip(f_big - 1, 0, None)
    emb_big = RED * np.minimum(f_big, 1) + lift_b * (np.array([236, 92, 98]) - RED) * 1.6
    emb_big = np.clip(emb_big + RED - emb_big[a_big > 0.9].mean(0), 0, 255)
    base_big = cv2.resize(base, (wc * S, hc * S), interpolation=cv2.INTER_CUBIC)
    big = a_big[..., None] * emb_big + (1 - a_big[..., None]) * base_big
    cv2.imwrite(str(WORK / f"{name}_word_render_x{S}.png"),
                cv2.cvtColor(np.clip(big, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR))

    cv2.imwrite(str(POSTS / f"{name}_embroidered.png"), cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    return out


def main():
    outs = [embroider_post(n) for n in ("POST_04", "POST_05", "POST_06")]
    grid = np.concatenate(outs, axis=1)
    cv2.imwrite(str(GRID / "grid_preview_embroidered.png"), cv2.cvtColor(grid, cv2.COLOR_RGB2BGR))


if __name__ == "__main__":
    main()
