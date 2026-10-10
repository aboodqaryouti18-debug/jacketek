"""Step 3: bake each patch from the website renders (step 2, harness).

The harness renders the patch shape in one neutral light thread (#ECE7DC) with
the site's createImageEmbroidery (fill-stitch relief, sheen, raised edge) and
the merrowed border with createLetteringEmbroidery (satin across the band).
Those renders carry ONLY the light: shading S = render luminance / its mean on
the flat face. The patch keeps its own artwork pixels and is lit by S, the
per-pixel form of the site's ThreadDyes formula (luminance x colour / mean
luminance), so the artwork's colours stay as they are on average.

-> work/patches/baked/<name>_thread.png  (RGBA, work resolution)
   work/patches/baked/<name>_shadow.png  (site contact shadow, alpha)
"""
import json
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi

W = "/home/user/jacketek/work/patches"
NAMES = ["porsche", "bmo", "lifeexe", "whocares", "cat"]
LUM = np.array([0.2126, 0.7152, 0.0722])

def rgba(p):
    return np.asarray(Image.open(p).convert("RGBA")).astype(np.float64) / 255

def shading(r, alpha):
    lum = r[..., :3] @ LUM
    solid = ndi.binary_erosion(alpha > 0.99, iterations=8)
    return lum / np.median(lum[solid])

def bake(n):
    m = json.load(open(f"{W}/{n}.json"))
    art = rgba(f"{W}/{n}_art.png")
    a = art[..., 3]
    img = rgba(f"{W}/render/{n}_image/render_thread.png")
    sh = rgba(f"{W}/render/{n}_image/render_shadow.png")[..., 3]
    S = shading(img, a)
    try:
        ring = rgba(f"{W}/render/{n}_ring/render_thread.png")
        ra = ring[..., 3]
        lum = ring[..., :3] @ LUM
        core = ndi.binary_erosion(rgba(f"{W}/{n}_ring.png")[..., 3] > 0.9, iterations=2)
        Sr = lum / np.median(lum[core])
        S = S * (1 - ra) + Sr * ra
    except FileNotFoundError:
        pass
    # compress the light range a touch: matte thread, never plastic highlights
    S = 1 + (S - 1) * 0.85
    col = np.clip(art[..., :3] * S[..., None], 0, 1)
    import os; os.makedirs(f"{W}/baked", exist_ok=True)
    out = np.dstack([col, a])
    Image.fromarray((out * 255).round().astype(np.uint8), "RGBA").save(f"{W}/baked/{n}_thread.png")
    Image.fromarray((sh * 255).round().astype(np.uint8)).save(f"{W}/baked/{n}_shadow.png")
    print(n, "S range", np.percentile(S[a > 0.5], [1, 50, 99]).round(3))

if __name__ == "__main__":
    for n in NAMES:
        bake(n)
