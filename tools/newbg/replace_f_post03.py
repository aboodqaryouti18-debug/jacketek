"""Post 03: the F patch replaced with the supplied JK patch photo (source/jk_patch_post03.webp).
The F patch is a tilted square of felt with pinked edges. Its exact footprint
(work/newbg/POST_03_Fpatch_mask.png) and corner quad, measured on the post, are kept:
the photo (square-cropped, centred, uniform scale) is mapped onto the same quad and
shown inside the same footprint, so position, tilt, size, edge and shadow stay as they
were. Only those pixels change. Posts 01, 02, 04-06 are copied byte for byte.
-> export/six_posts_jk_post03/"""
import shutil
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
PREV = ROOT / "export/six_posts_l_photos"; OUT = ROOT / "export/six_posts_jk_post03"
QUAD = np.float32([[293, 169], [898, 233], [837, 847], [219, 779]])   # TL TR BR BL of the F patch
SS = 3

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for i in (1, 2, 4, 5, 6): shutil.copyfile(PREV / f"POST_0{i}.png", OUT / f"POST_0{i}.png")
    post = cv2.imread(str(PREV / "POST_03.png")).astype(np.float32)
    src = cv2.imread(str(ROOT / "source/jk_patch_post03.webp")).astype(np.float32)
    h, w = src.shape[:2]; s = min(h, w)
    x0, y0 = (w - s) / 2, (h - s) / 2                       # centred square crop
    rect = np.float32([[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]])
    Hm = cv2.getPerspectiveTransform(rect, QUAD * SS)
    k = np.sqrt(abs(np.linalg.det(Hm[:2, :2])))
    if k < 1: src = cv2.GaussianBlur(src, (0, 0), 0.45 / k)
    big = cv2.warpPerspective(src, Hm, (1080 * SS, 1350 * SS), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    img = cv2.resize(big, (1080, 1350), interpolation=cv2.INTER_AREA)
    m = cv2.imread(str(ROOT / "work/newbg/POST_03_Fpatch_mask.png"), 0).astype(np.float32) / 255
    a = cv2.GaussianBlur(m, (0, 0), 0.7)[..., None]
    out = np.clip(img * a + post * (1 - a), 0, 255).round().astype(np.uint8)
    cv2.imwrite(str(OUT / "POST_03.png"), out)
    ch = np.abs(out.astype(int) - post.round().astype(int)).max(2) > 0
    outside = ch & (cv2.dilate((m > 0).astype(np.uint8), np.ones((5, 5))) == 0)
    print("changed px", int(ch.sum()), "outside the patch footprint", int(outside.sum()))
    full = [cv2.imread(str(OUT / f"POST_0{i}.png")) for i in range(1, 7)]
    grid = np.vstack([np.hstack(full[:3]), np.hstack(full[3:])])
    cv2.imwrite(str(OUT / "six_posts_full.png"), grid)
    cv2.imwrite(str(OUT / "six_posts_preview.jpg"), cv2.resize(grid, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 92])
    cv2.imwrite(str(OUT / "compare_POST_03.jpg"), np.hstack([post.astype(np.uint8), np.full((1350, 16, 3), 255, np.uint8), out]), [cv2.IMWRITE_JPEG_QUALITY, 92])
