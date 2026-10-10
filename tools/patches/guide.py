"""Step 2a: relief guides for the harness (input to createImageEmbroidery).

The site splits an image into tonal areas, one satin angle each. Product
photos of real patches carry their own stitch grain and lighting, which would
become random grooves, so the guide is the artwork clustered into its design
colours (k-means). The guide only drives relief: the baked colours come from
the untouched artwork (bake.py).
"""
import numpy as np, cv2
from PIL import Image
W = "/home/user/jacketek/work/patches"
K = {"porsche": 7, "bmo": 9, "lifeexe": 5, "whocares": 5, "cat": 7}
for n, k in K.items():
    a = np.asarray(Image.open(f"{W}/{n}_art.png").convert("RGBA")).copy()
    g = cv2.medianBlur(a[..., :3], 7)
    g = cv2.bilateralFilter(g, 9, 40, 7)
    m = a[..., 3] > 127
    px = g[m].reshape(-1, 3).astype(np.float32)
    _, lab, cen = cv2.kmeans(px, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    # one design colour photographed under uneven light splits in two:
    # merge clusters closer than 34 (RGB) into one area
    cen = cen.copy()
    for i in range(k):
        for j in range(i):
            if np.linalg.norm(cen[i] - cen[j]) < 34:
                cen[i] = cen[j]
    q = g.copy()
    q[m] = cen[lab.ravel()].astype(np.uint8)
    q = cv2.medianBlur(q, 5)
    Image.fromarray(np.dstack([q, a[..., 3]]), "RGBA").save(f"{W}/{n}_guide.png")
    print(n, k)
