"""Find where each original render appears inside posts 04-06 (similarity transform
render -> post, via SIFT + RANSAC), so the new photo with the same framing can be
placed with the identical transform."""
import json, sys
import cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
POSTS = {n: ROOT / "export/website_embroidery" / f"POST_0{n}_website_embroidery.png" for n in (4, 5, 6)}
RENDERS = {k: ROOT / "source/renders" / f for k, f in {
    "back": "02_back.png", "front": "03_front_full.png", "chest": "04_chest_letters.png",
    "number": "05_sleeve_number.png", "collar": "06_collar.png", "patch": "01_sleeve_patch.png"}.items()}
sift = cv2.SIFT_create(nfeatures=8000)
def feats(img, scale):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
    k, d = sift.detectAndCompute(g, None)
    return [(p.pt[0] / scale, p.pt[1] / scale) for p in k], d
out = {}
for n, pp in POSTS.items():
    post = cv2.imread(str(pp)); pk, pd = feats(post, 3)
    for name, rp in RENDERS.items():
        r = cv2.imread(str(rp), cv2.IMREAD_COLOR); rk, rd = feats(r, 1.5)
        m = cv2.BFMatcher(cv2.NORM_L2).knnMatch(rd, pd, k=2)
        good = [a for a, b in m if a.distance < 0.75 * b.distance]
        if len(good) < 8: continue
        src = np.float32([rk[g.queryIdx] for g in good]); dst = np.float32([pk[g.trainIdx] for g in good])
        M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=20000)
        ni = int(inl.sum()) if inl is not None else 0
        if M is None or ni < 12: continue
        s = float(np.hypot(M[0, 0], M[1, 0])); ang = float(np.degrees(np.arctan2(M[1, 0], M[0, 0])))
        h, w = r.shape[:2]; corners = cv2.transform(np.float32([[[0, 0], [w, 0], [w, h], [0, h]]]), M)[0]
        print(f"POST_0{n} <- {name:7s} inliers {ni:4d}/{len(good):4d} scale {s:.3f} rot {ang:+.2f}deg corners {corners.round(0).tolist()}")
        out.setdefault(f"POST_0{n}", []).append(dict(render=name, inliers=ni, M=M.tolist(), corners=corners.tolist(), size=[w, h]))
(ROOT / "work/replace_photos/locate.json").write_text(json.dumps(out, indent=1))
