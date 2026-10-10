"""Map each live-site capture (work/rebuild/site, 3x) onto its card window in the
original POST_05 (SIFT + RANSAC homography, then ECC refinement on the window).
-> work/rebuild/cards.json: H_panel (capture px -> panel px) and H_out (-> 1080x1350)"""
import json, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/rebuild"))
import compose as C
CARDS = {"card1": "body_panel.png", "card2": "embroidery_panel.png"}
UP = 4   # the original card is matched at 4x panel px

def main():
    F = {f["id"]: f for f in json.loads((ROOT / "work/rebuild/frames.json").read_text())["POST_05"]}
    g = cv2.imread(str(ROOT / "source/grid_preview_original.webp"))[:, 667:1333]
    gray = cv2.cvtColor(g, cv2.COLOR_BGR2GRAY)
    out = {}
    for cid, fn in CARDS.items():
        cap = cv2.cvtColor(cv2.imread(str(ROOT / "work/rebuild/site" / fn)), cv2.COLOR_BGR2GRAY)
        win = np.array(F[cid]["window"]); x0, y0 = np.floor(win.min(0)).astype(int) - 2; x1, y1 = np.ceil(win.max(0)).astype(int) + 2
        crop = cv2.resize(gray[y0:y1, x0:x1], None, fx=UP, fy=UP, interpolation=cv2.INTER_CUBIC)
        # the capture scaled near the card's size first
        k = (x1 - x0) * UP / (cap.shape[1] * 0.85)
        capk = cv2.resize(cap, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        sift = cv2.SIFT_create(8000)
        ka, da = sift.detectAndCompute(capk, None); kb, db = sift.detectAndCompute(crop, None)
        mt = cv2.BFMatcher().knnMatch(da, db, k=2)
        good = [m for m, n in mt if m.distance < 0.75 * n.distance]
        pa = np.float32([ka[m.queryIdx].pt for m in good]); pb = np.float32([kb[m.trainIdx].pt for m in good])
        Hk, inl = cv2.findHomography(pa, pb, cv2.RANSAC, 3.0)
        # capture px -> crop(4x) px
        H = Hk @ np.diag([k, k, 1])
        # ECC refinement (window interior, both at 4x panel)
        wm = np.zeros(crop.shape, np.uint8)
        cv2.fillPoly(wm, [np.int32((win - [x0, y0]) * UP)], 1); wm = cv2.erode(wm, np.ones((9, 9)))
        warped = cv2.warpPerspective(cv2.GaussianBlur(cap, (0, 0), 1.0), H, crop.shape[::-1], flags=cv2.INTER_LINEAR)
        try:
            Wh = np.eye(3, dtype=np.float32)
            _, Wh = cv2.findTransformECC(crop.astype(np.float32), warped.astype(np.float32), Wh, cv2.MOTION_HOMOGRAPHY,
                                         (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), wm, 5)
            H = np.linalg.inv(Wh.astype(np.float64)) @ H
            ecc = True
        except cv2.error:
            ecc = False
        Hp = np.diag([1 / UP, 1 / UP, 1]) @ H
        Hp = np.array([[1, 0, x0], [0, 1, y0], [0, 0, 1.0]]) @ Hp           # -> panel px
        Hout = C.A("POST_05") @ Hp
        # quality: correlation inside the window
        chk = cv2.warpPerspective(cap, H, crop.shape[::-1], flags=cv2.INTER_AREA)
        a = crop[wm > 0].astype(float); b = chk[wm > 0].astype(float)
        ncc = float(np.corrcoef(a, b)[0, 1])
        out[cid] = dict(file=fn, inliers=int(inl.sum()), ecc=ecc, ncc=round(ncc, 4), H_panel=Hp.tolist(), H_out=Hout.tolist())
        print(cid, "inliers", int(inl.sum()), "of", len(good), "ecc", ecc, "ncc", round(ncc, 4))
        vis = np.dstack([crop, chk, crop]); cv2.imwrite(str(ROOT / f"work/rebuild/{cid}_fit_x4.png"), vis)
    (ROOT / "work/rebuild/cards.json").write_text(json.dumps(out, indent=1))

if __name__ == "__main__":
    main()
