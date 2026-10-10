import json, cv2, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
L = json.loads((ROOT / "work/replace_photos/locate.json").read_text())
sift = cv2.SIFT_create(nfeatures=12000)
def run(post_n, render, exclude, scale_post=3, region=None):
    post = cv2.imread(str(ROOT / f"export/website_embroidery/POST_0{post_n}_website_embroidery.png"))
    g = cv2.resize(cv2.cvtColor(post, cv2.COLOR_BGR2GRAY), None, fx=scale_post, fy=scale_post, interpolation=cv2.INTER_CUBIC)
    mask = np.full(g.shape, 255, np.uint8)
    for c in exclude: cv2.fillPoly(mask, [np.int32(np.array(c) * scale_post)], 0)
    if region:
        rm = np.zeros_like(mask); x0, y0, x1, y1 = [v * scale_post for v in region]; rm[y0:y1, x0:x1] = 255; mask &= rm
    pk, pd = sift.detectAndCompute(g, mask)
    r = cv2.imread(str(ROOT / "source/renders" / render)); best = None
    for rs in (0.5, 0.75, 1.0, 1.5, 2.0):
        rg = cv2.resize(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), None, fx=rs, fy=rs, interpolation=cv2.INTER_AREA if rs < 1 else cv2.INTER_CUBIC)
        rk, rd = sift.detectAndCompute(rg, None)
        if rd is None or pd is None: continue
        m = cv2.BFMatcher().knnMatch(rd, pd, k=2); good = [a for a, b in m if a.distance < 0.8 * b.distance]
        if len(good) < 8: continue
        src = np.float32([(rk[x.queryIdx].pt[0] / rs, rk[x.queryIdx].pt[1] / rs) for x in good])
        dst = np.float32([(pk[x.trainIdx].pt[0] / scale_post, pk[x.trainIdx].pt[1] / scale_post) for x in good])
        M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=2.0, maxIters=20000)
        if M is None: continue
        ni = int(inl.sum()); s = np.hypot(M[0, 0], M[1, 0])
        if s > 0.05 and (best is None or ni > best[0]): best = (ni, M, len(good), rs)
    if best:
        ni, M, ng, rs = best; h, w = r.shape[:2]
        c = cv2.transform(np.float32([[[0, 0], [w, 0], [w, h], [0, h]]]), M)[0]
        print(f"POST_0{post_n} <- {render}: inliers {ni}/{ng} (render scale {rs}) scale {np.hypot(M[0,0],M[1,0]):.3f} rot {np.degrees(np.arctan2(M[1,0],M[0,0])):+.2f} corners {c.round(0).tolist()}")
        return dict(render=render, inliers=ni, M=M.tolist(), corners=c.tolist(), size=[w, h])
    print(f"POST_0{post_n} <- {render}: no match")
big04 = [e for e in L["POST_04"] if e["render"] == "back"][0]["corners"]
r1 = run(4, "02_back.png", [big04], region=(380, 540, 667, 800))
six = [e["corners"] for e in L["POST_06"] if e["render"] in ("chest", "number")]
r2 = run(6, "06_collar.png", six, region=(300, 330, 667, 600))
L["POST_04_small"] = r1; L["POST_06_collar"] = r2
(ROOT / "work/replace_photos/locate.json").write_text(json.dumps(L, indent=1))
