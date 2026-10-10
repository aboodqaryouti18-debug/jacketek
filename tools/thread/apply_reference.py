"""The reference background treatment (source/reference_dots_thread.jpg), traced, on the
latest original six posts (inputs untouched):
  dots    the reference's grid: 78.25 x 75.25 px, first dot at (60, 60) in every post,
          small round dots, tone-on-tone (cream on navy, navy on beige, palette only)
  thread  the reference's thread, traced (work/trace/route.json: its visible stretches,
          snapped to its own dashes), joined in the reference's order: where the reference
          hides the thread behind content, the join is a smooth curve along both ends'
          tangents. Dash 22 px / gap 14 px (period 36, measured), 5 px wide, cream on navy,
          navy on beige: the colour switches exactly at the post edges.
Coordinates: the reference tiles the six full 4:5 posts (F: 3240 x 2700 px).
Everything is drawn on background pixels only (work/thread/POST_0X_fg.png).
-> export/six_posts_reference_bg/"""
import json, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/thread"))
from masks import FINAL
OUT = ROOT / "export/six_posts_reference_bg"; W = ROOT / "work/thread"
POS = {"POST_01": (0, 0), "POST_02": (1, 0), "POST_03": (2, 0), "POST_04": (0, 1), "POST_05": (1, 1), "POST_06": (2, 1)}
STYLE = {"POST_01": "navy", "POST_02": "beige", "POST_03": "navy", "POST_04": "beige", "POST_05": "navy", "POST_06": "beige"}
CREAM, NAVY = (0xFC, 0xF0, 0xD6), (0x00, 0x30, 0x49)
DOT = dict(sx=78.25, sy=75.25, x0=60.0, y0=60.0, r=2.1, mix={"navy": (CREAM, 0.32), "beige": (NAVY, 0.26)})
DASH, GAP, WIDTH = 22.0, 14.0, 5.0
SS = 3
# strands: the traced stretches in the reference's order ("-" = traversed backwards); the
# reference's thread leaves and re-enters the grid at its outer edges, so a strand ends there
STRANDS = [
    ["01_top_to_02", "02_03_loop_F", "03_F_to_edge"],
    ["01_big_curve", "02_03_06_low", "06_05_mid", "-05_top_curve", "05_life_to_04", "-04_left_a"],
    ["04_left_clock", "04_clock_right", "04_05_bottom", "05_06_bmo", "06_bmo_right"],
    ["04_top_curve"],
]
EDGE_EXT = 40.0

def tangent(P, end, n=25):
    if end: v = P[-1] - P[max(0, len(P) - n)]
    else: v = P[min(len(P) - 1, n)] - P[0]
    return v / (np.linalg.norm(v) + 1e-9)

def hermite(p0, t0, p1, t1):
    L = np.linalg.norm(p1 - p0); m0, m1 = t0 * L * 0.9, t1 * L * 0.9
    u = np.linspace(0, 1, max(8, int(L)))[:, None]
    h00, h10, h01, h11 = 2*u**3 - 3*u**2 + 1, u**3 - 2*u**2 + u, -2*u**3 + 3*u**2, u**3 - u**2
    return h00 * p0 + h10 * m0 + h01 * p1 + h11 * m1

def fg_global():
    G = np.zeros((2700, 3240), np.float32)
    for post, (c, r) in POS.items():
        G[r * 1350:(r + 1) * 1350, c * 1080:(c + 1) * 1080] = cv2.imread(str(W / f"{post}_fg.png"), 0) / 255.0
    return G

def tuck(J, FG):
    """a hidden join: keep it only until it first goes under content from each end
    (the reference hides it there); a join that never meets content is kept whole"""
    xi = np.clip(J[:, 0].astype(int), 0, 3239); yi = np.clip(J[:, 1].astype(int), 0, 2699)
    hit = FG[yi, xi] > 0.5
    if not hit.any(): return [J]
    a = int(np.argmax(hit)); b = len(J) - 1 - int(np.argmax(hit[::-1]))
    pad = 12                          # run on a little under the content
    return [J[:min(len(J), a + pad)], J[max(0, b - pad):]]

def strands():
    R = json.loads((ROOT / "work/trace/route.json").read_text())
    out = []
    for names in STRANDS:
        parts = []
        for nm in names:
            rev = nm.startswith("-"); P = np.array(R[nm.lstrip("-")]["points"], float)
            if rev: P = P[::-1]
            parts.append(P)
        # stretches that touch the grid's outer edge run on past it
        for i, P in enumerate(parts):
            for end in (False, True):
                p = P[-1] if end else P[0]
                if p[0] < 12 or p[0] > 3228 or p[1] < 12 or p[1] > 2688:
                    t = tangent(P, end) * (1 if end else -1)
                    ext = p + t * EDGE_EXT
                    parts[i] = np.vstack([P, ext]) if end else np.vstack([ext, P])
                    P = parts[i]
        FG = fg_global()
        S = [parts[0]]
        for P in parts[1:]:
            a = S[-1][-1]; b = P[0]
            J = hermite(a, tangent(S[-1], True), b, tangent(P, False))[1:-1]
            k = tuck(J, FG)
            if len(k) == 1: S[-1] = np.vstack([S[-1], k[0], P])
            else:
                S[-1] = np.vstack([S[-1], k[0]])
                S.append(np.vstack([k[1], P]))
        out += S
    return out

def resample(P, step=0.5):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    s = np.arange(0, d[-1], step)
    return np.c_[np.interp(s, d, P[:, 0]), np.interp(s, d, P[:, 1])], s

FGD = None
def thread_alpha(post, paths):
    """whole dashes only: a dash that would touch content (or its 8 px margin) is hidden
    entirely, so the thread passes cleanly behind text and prints (no slivers in gaps)"""
    global FGD
    if FGD is None:
        FGD = cv2.dilate((fg_global() > 0.3).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (17, 17)))
    c, r = POS[post]; ox, oy = c * 1080, r * 1350
    canvas = np.zeros((1350 * SS, 1080 * SS), np.uint8)
    for P, s in paths:
        on = (s % (DASH + GAP)) < DASH
        e = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
        for a, b in zip(e[::2], e[1::2]):
            q = P[a:b]; xi = np.clip(q[:, 0].astype(int), 0, 3239); yi = np.clip(q[:, 1].astype(int), 0, 2699)
            if FGD[yi, xi].any(): continue
            seg = (P[a:b] - [ox, oy]) * SS
            if seg[:, 0].max() < -30 or seg[:, 0].min() > 1080 * SS + 30 or seg[:, 1].max() < -30 or seg[:, 1].min() > 1350 * SS + 30: continue
            cv2.polylines(canvas, [np.int32(np.round(seg * 4))], False, 255, int(round(WIDTH * SS)), cv2.LINE_AA, shift=2)
    return cv2.resize(canvas.astype(np.float32) / 255, (1080, 1350), interpolation=cv2.INTER_AREA)

def dots_alpha():
    yy, xx = np.mgrid[0:1350, 0:1080].astype(np.float32) + 0.5
    fx = (xx - DOT["x0"]) % DOT["sx"]; fx = np.minimum(fx, DOT["sx"] - fx)
    fy = (yy - DOT["y0"]) % DOT["sy"]; fy = np.minimum(fy, DOT["sy"] - fy)
    return np.clip(DOT["r"] + 0.5 - np.hypot(fx, fy), 0, 1)

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [resample(P) for P in strands()]
    (W / "reference_thread_full.json").write_text(json.dumps([P.round(2).tolist() for P, _ in paths]))
    dots = dots_alpha(); report = {}
    for post in POS:
        st = STYLE[post]
        img = cv2.cvtColor(cv2.imread(str(FINAL[post])), cv2.COLOR_BGR2RGB).astype(np.float32)
        fg = cv2.imread(str(W / f"{post}_fg.png"), 0).astype(np.float32) / 255
        strict = (fg < 0.3).astype(np.float32)
        bgw = (1 - np.clip(cv2.GaussianBlur(cv2.dilate(fg, np.ones((3, 3))), (0, 0), 0.8), 0, 1)) * strict
        bgt = (1 - np.clip(cv2.GaussianBlur(cv2.dilate(fg, np.ones((7, 7))), (0, 0), 1.0), 0, 1)) * strict
        dc, dk = DOT["mix"][st]; da = dots * bgw * dk
        out = img * (1 - da[..., None]) + np.float32(dc) * da[..., None]
        ta = thread_alpha(post, paths) * bgt
        tc = CREAM if st == "navy" else NAVY
        out = out * (1 - ta[..., None]) + np.float32(tc) * ta[..., None]
        o8 = np.clip(out, 0, 255).round().astype(np.uint8)
        cv2.imwrite(str(OUT / f"{post}.png"), cv2.cvtColor(o8, cv2.COLOR_RGB2BGR))
        ch = np.abs(o8.astype(int) - img.round().astype(int)).max(2) > 0
        report[post] = dict(changed_px=int(ch.sum()), changed_on_content_px=int((ch & (fg >= 0.3)).sum()))
    full = [cv2.imread(str(OUT / f"{p}.png")) for p in POS]
    grid = np.vstack([np.hstack(full[:3]), np.hstack(full[3:])])
    cv2.imwrite(str(OUT / "six_posts_full.png"), grid)
    ref = cv2.imread(str(ROOT / "source/reference_dots_thread.jpg"))
    g2 = cv2.resize(grid, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT / "compare_with_reference.jpg"), np.hstack([ref, np.full((ref.shape[0], 12, 3), 255, np.uint8), g2]), [cv2.IMWRITE_JPEG_QUALITY, 92])
    (OUT / "report.json").write_text(json.dumps(report, indent=1)); print(json.dumps(report))
