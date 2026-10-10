"""Cut the JK / 27 / 09 designs out of the original jacket renders (source/renders),
for uploading to the live configurator as the zone designs shown on POST_05's
embroidery card (the card's thumbnails show these same three designs)."""
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
R = "source/renders"; O = "work/rebuild/thumbs"

def save(name, rgb, m, holes=True):
    m = ndi.binary_closing(m, iterations=2)
    if holes: m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m); sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.isin(lab, 1 + np.nonzero(sizes > sizes.max() * 0.2)[0])
    ys, xs = np.nonzero(keep); y0, y1, x0, x1 = max(0, ys.min() - 4), ys.max() + 5, max(0, xs.min() - 4), xs.max() + 5
    a = cv2.GaussianBlur(keep.astype(np.float32), (0, 0), 0.7)
    Image.fromarray(np.dstack([rgb, (a * 255).astype(np.uint8)])[y0:y1, x0:x1], "RGBA").save(f"{O}/{name}.png")

im = np.asarray(Image.open(f"{R}/04_chest_letters.png").convert("RGB")); a = im.astype(int)
m = ~((a[..., 2] - a[..., 0] > 22) & (a[..., 2] - a[..., 1] > 8)); m[:, :520] = False
m = ndi.binary_opening(m, iterations=2)            # letters only (not the snaps)
save("JK", im, m)
im = np.asarray(Image.open(f"{R}/02_back.png").convert("RGB")); a = im.astype(int)
m = (a[..., 0] - a[..., 2] > 40) | ((np.abs(a[..., 0] - a[..., 2]) < 25) & (a.mean(2) > 120) & (a.mean(2) < 215))
m[:95] = False; m[:, :215] = False; m[:, 470:] = False             # the "27" block
save("27", im, m)
im = np.asarray(Image.open(f"{R}/05_sleeve_number.png").convert("RGB")); a = im.astype(int)
m = (a.mean(2) < 175) & ~(a[..., 2] - a[..., 0] > 60); m[:, 300:] = False; m[:, :45] = False; m[:150] = False; m[380:] = False
m = ndi.binary_opening(m, iterations=4)   # drops the thin shadow of the sleeve edge
save("09", im, m, holes=False)   # keep the 0 / 9 counters open
print("ok")
