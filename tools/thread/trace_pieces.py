"""Chain the reference's dash marks into the visible stretches of its thread.
Only marks on true background count (local colour = the panel's navy / beige).
-> work/trace/pieces.json (reference px), work/trace/pieces_overlay.png (numbered)"""
import json
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "source/reference_dots_thread.jpg"
XB, YB = [0, 425, 855, 1280], [0, 531, 1065]
STYLE = [["navy", "beige", "navy"], ["beige", "navy", "beige"]]

def marks():
    a = cv2.imread(str(REF)).astype(np.float32)[..., ::-1]
    L = a @ [0.299, 0.587, 0.114]
    big = cv2.medianBlur(a.astype(np.uint8), 21).astype(np.float32)        # local background colour
    out = []
    for r in range(2):
        for c in range(3):
            x0, x1, y0, y1 = XB[c] + 1, XB[c + 1] - 1, YB[r] + 1, YB[r + 1] - 1
            ref = np.median(big[y0 + 5:y0 + 40, x0 + 5:x1 - 5].reshape(-1, 3), 0) if False else None
            p = L[y0:y1, x0:x1]; bgL = cv2.medianBlur(p.astype(np.uint8), 15).astype(np.float32)
            nav = STYLE[r][c] == "navy"
            d = (p - bgL) if nav else (bgL - p)
            loc = big[y0:y1, x0:x1]
            if nav:   # background: dark navy around
                isbg = (loc @ [0.299, 0.587, 0.114] < 70) & (loc[..., 2] - loc[..., 0] > 20)
            else:     # background: warm beige (not the white polaroid frames, not photos)
                isbg = (loc[..., 0] - loc[..., 2] > 22) & (loc @ [0.299, 0.587, 0.114] > 190)
            isbg = cv2.erode(isbg.astype(np.uint8), np.ones((3, 3))) > 0
            m = (d > 40).astype(np.uint8)
            n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
            for i in range(1, n):
                if not (5 <= st[i, 4] <= 60): continue
                ys, xs = np.nonzero(lab == i)
                if isbg[int(ys.mean()), int(xs.mean())] == 0: continue
                pts = np.c_[xs, ys].astype(float)
                ev, evec = np.linalg.eigh(np.cov(pts.T))
                ln, wd = 4 * np.sqrt(max(ev[1], 1e-6)), 4 * np.sqrt(max(ev[0], 1e-6))
                if ln < 4.5 or ln / max(wd, .5) < 2.0: continue
                out.append(dict(x=float(xs.mean() + x0), y=float(ys.mean() + y0), d=evec[:, 1].tolist(), ln=float(ln), wd=float(wd), style=STYLE[r][c]))
    return out

def chain(M, maxd=14.0, maxang=40):
    P = np.array([[m["x"], m["y"]] for m in M]); D = np.array([m["d"] for m in M])
    n = len(P); nb = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            v = P[j] - P[i]; dist = np.hypot(*v)
            if dist > maxd or dist < 2: continue
            u = v / dist
            if abs(u @ D[i]) > np.cos(np.radians(maxang)) and abs(u @ D[j]) > np.cos(np.radians(maxang)):
                nb[i].append(j); nb[j].append(i)
    seen = np.zeros(n, bool); pieces = []
    # start from endpoints (degree 1) first
    order = sorted(range(n), key=lambda k: len(nb[k]))
    for s in order:
        if seen[s]: continue
        path = [s]; seen[s] = True
        for direction in (0, 1):
            cur = path[-1] if direction == 0 else path[0]
            prev = None if len(path) < 2 else (path[-2] if direction == 0 else path[1])
            while True:
                cand = [k for k in nb[cur] if not seen[k]]
                if not cand: break
                if prev is not None:
                    v0 = P[cur] - P[prev]; v0 /= np.linalg.norm(v0)
                    cand.sort(key=lambda k: -((P[k] - P[cur]) / np.linalg.norm(P[k] - P[cur])) @ v0)
                nxt = cand[0]; seen[nxt] = True
                if direction == 0: path.append(nxt)
                else: path.insert(0, nxt)
                prev, cur = cur, nxt
        if len(path) >= 3: pieces.append(path)
    return P, pieces

if __name__ == "__main__":
    M = marks(); P, pieces = chain(M)
    out = [[P[k].round(1).tolist() for k in pc] for pc in pieces]
    (ROOT / "work/trace/pieces.json").write_text(json.dumps(out))
    vis = cv2.imread(str(REF)); vis = cv2.resize(vis, None, fx=1.5, fy=1.5)
    rng = np.random.default_rng(3)
    for i, pc in enumerate(out):
        col = tuple(int(v) for v in rng.integers(60, 255, 3))
        q = np.int32(np.array(pc) * 1.5)
        cv2.polylines(vis, [q], False, (0, 0, 255), 2)
        cv2.putText(vis, str(i), tuple(q[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(vis, str(i) + "e", tuple(q[-1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
    cv2.imwrite(str(ROOT / "work/trace/pieces_overlay.png"), vis)
    print(len(M), "marks;", len(out), "pieces:", [len(p) for p in out])
