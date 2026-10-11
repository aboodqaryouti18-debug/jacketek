"""Background layer at 3240 x 4050 for each post, reconstructed as vector + smooth surface,
matching the approved background (the supplied image, export/six_posts_new_background plates):
  surface  the supplied image's navy / beige surface: its clean background pixels (no dots,
           thread or content), interpolated under its own content, enlarged 3x (it is a smooth
           field, so enlarging adds no visible softness), + the site's textile grain at 3x native
  dots     every dot visible in the approved post, at its measured position (centroid in the
           approved plate), drawn as an antialiased disc at 3x; colour + size measured
  thread   the traced thread (work/trace/route.json), dashes phase-locked to the approved
           plate, drawn as round-capped dashes at 3x; colour + width + dash length measured
Everything in one coordinate system (the six-post grid), so dots and thread stay continuous.
-> work/psd_assets/bg/POST_0X_background.png (+ .svg of the dots and thread)"""
import json, sys
from pathlib import Path
import cv2, numpy as np
from scipy.ndimage import map_coordinates
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/newbg"))
import replace_background as RB
K = 3; W, H = 1080 * K, 1350 * K
OUT = ROOT / "work/psd_assets/bg"; OUT.mkdir(parents=True, exist_ok=True)
LUM = RB.LUM

def surface(post):
    pl = RB.plate_raw(post); bg, clean = RB.plate_bg_mask(post, pl)
    med = cv2.medianBlur(pl.astype(np.uint8), 15).astype(np.float32)
    w = cv2.erode(clean.astype(np.uint8), np.ones((5, 5))).astype(np.float32)
    out = np.zeros_like(med)
    for sig in (6, 20, 60, 200):          # normalised convolution, coarser where nothing is known
        num = cv2.GaussianBlur(med * w[..., None], (0, 0), sig); den = cv2.GaussianBlur(w, (0, 0), sig)
        est = num / np.maximum(den, 1e-6)[..., None]
        if sig == 6: out = est; known = den
        else: out = np.where((known < 0.15)[..., None], est, out); known = np.maximum(known, den)
    out = np.where(w[..., None] > 0, cv2.GaussianBlur(med, (0, 0), 2), out)
    out = cv2.GaussianBlur(out, (0, 0), 3)
    return out

def detect_dots(post, approved_plate, fg):
    pl = approved_plate; L = pl @ LUM
    base = cv2.medianBlur(pl.astype(np.uint8), 15).astype(np.float32)
    d = (L - base @ LUM) if RB.STYLE[post] == "navy" else (base @ LUM - L)
    th = RB.thread_mask(post)
    m = ((d > 12) & ~cv2.dilate(th.astype(np.uint8), np.ones((5, 5))).astype(bool)).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    dots = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if not (3 <= a <= 45 and w <= 9 and h <= 9): continue
        cx, cy = cen[i]
        if fg[int(cy), int(cx)] > 0.3: continue           # only dots the approved post shows
        ys, xs = np.mgrid[max(0, y - 2):min(1350, y + h + 2), max(0, x - 2):min(1080, x + w + 2)]
        wt = np.clip(d[ys, xs], 0, None)
        dots.append((float((xs * wt).sum() / wt.sum()), float((ys * wt).sum() / wt.sum()), pl[int(round(cy)), int(round(cx))].tolist(), float(d[int(cy), int(cx)])))
    return dots

def thread_paths():
    R = json.loads((ROOT / "work/trace/route.json").read_text())
    return {k: np.array(v["points"], float) for k, v in R.items()}

def resample(P, step=0.25):
    dd = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]; s = np.arange(0, dd[-1], step)
    return np.c_[np.interp(s, dd, P[:, 0]), np.interp(s, dd, P[:, 1])], s

def full_plates():
    G = np.zeros((2700, 3240, 3), np.float32)
    for post, (c, r) in RB.POS.items():
        G[r * 1350:(r + 1) * 1350, c * 1080:(c + 1) * 1080] = cv2.cvtColor(cv2.imread(str(ROOT / "work/newbg" / f"{post}_plate.png")), cv2.COLOR_BGR2RGB)
    return G

def fit_dashes(G, P, style_at):
    """dash period / length / phase along one stretch, from the approved plates (1080 grid)"""
    Q, s = resample(P, 0.5)
    T = np.gradient(Q, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9; N = np.c_[-T[:, 1], T[:, 0]]
    L = G @ LUM; base = cv2.medianBlur(np.clip(G, 0, 255).astype(np.uint8), 15).astype(np.float32) @ LUM
    dev = np.abs(L - base)
    prof = np.max([map_coordinates(dev, [Q[:, 1] + o * N[:, 1], Q[:, 0] + o * N[:, 0]], order=1) for o in np.arange(-3, 3.1, 0.5)], 0)
    best = None
    for per in np.arange(32, 40.1, 0.25):
        for duty in (0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8):
            for ph in np.arange(0, per, 0.5):
                on = ((s - ph) % per) < per * duty
                sc = prof[on].mean() - prof[~on].mean()
                if best is None or sc > best[0]: best = (sc, per, duty, ph)
    return dict(period=best[1], duty=best[2], phase=best[3], contrast=float(best[0]))

def measure_width(G, P):
    Q, s = resample(P, 1.0)
    T = np.gradient(Q, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9; N = np.c_[-T[:, 1], T[:, 0]]
    L = G @ LUM; offs = np.arange(-8, 8.1, 0.25)
    S = np.array([map_coordinates(L, [Q[:, 1] + o * N[:, 1], Q[:, 0] + o * N[:, 0]], order=1) for o in offs])
    S = np.abs(S - np.median(S, 0, keepdims=True))
    k = S.max(0) > np.percentile(S.max(0), 70)
    prof = []
    for j in np.flatnonzero(k):          # align each profile on its peak
        c = int(np.argmax(S[:, j])); 
        if 12 <= c < len(offs) - 12: prof.append(S[c - 12:c + 13, j] / S[c, j])
    p = np.mean(prof, 0); return float((p > 0.5).sum() * 0.25)

CREAM, NAVY = np.float32([0xFC, 0xF0, 0xD6]), np.float32([0x00, 0x30, 0x49])

def thread_colour(G, P, dash, style):
    """the median colour at the dash centres of this stretch, in the approved plates"""
    Q, s = resample(P, 1.0); on = ((s - dash["phase"]) % dash["period"]) < dash["period"] * dash["duty"] * 0.6
    xs = np.clip(Q[on, 0].astype(int), 0, 3239); ys = np.clip(Q[on, 1].astype(int), 0, 2699)
    return np.median(G[ys, xs], 0)

def svg_path(pts):
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts)

def render_all(G, paths, dash):
    grain = cv2.cvtColor(cv2.imread("/home/user/jacketportable/public/assets/texture/grain-soft-240.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32)
    report = {}
    for post, (c, r) in RB.POS.items():
        st = RB.STYLE[post]
        fg = cv2.imread(str(ROOT / "work/thread" / f"{post}_fg.png"), 0) / 255.0
        approved = cv2.cvtColor(cv2.imread(str(ROOT / "work/newbg" / f"{post}_plate.png")), cv2.COLOR_BGR2RGB).astype(np.float32)
        surf = np.clip(cv2.resize(surface(post), (W, H), interpolation=cv2.INTER_CUBIC), 0, 255)
        # textile grain (site asset, 240 px tile at 3x scale), soft-light, gentle
        g = cv2.resize(grain, (round(240 * K * 1080 / 1080 * 0.94),) * 2, interpolation=cv2.INTER_AREA)
        g = np.tile(g, (H // g.shape[0] + 1, W // g.shape[1] + 1, 1))[:H, :W]
        gv, ga = g[..., 0:1] / 255, g[..., 3:4] / 255 * 0.45
        b = surf / 255; soft = np.where(gv <= 0.5, b - (1 - 2 * gv) * b * (1 - b), b + (2 * gv - 1) * (np.sqrt(b) - b))
        img = (b * (1 - ga) + soft * ga) * 255
        svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
        # dots
        dots = detect_dots(post, approved, fg)
        if dots:
            dcol = np.median(np.array([d[2] for d in dots]), 0).astype(np.float32)
            svg.append(f'<g id="dots" fill="rgb({int(dcol[0])},{int(dcol[1])},{int(dcol[2])})">')
            SSA = 4; R = 1.9 * K
            for x, y, _, _ in dots:
                X, Y = (x + 0.5) * K, (y + 0.5) * K
                x0, y0 = int(X - R - 3), int(Y - R - 3); x1, y1 = int(X + R + 4), int(Y + R + 4)
                if x0 < 0 or y0 < 0 or x1 > W or y1 > H: continue
                yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + 0.5
                a = np.clip(R + 0.5 - np.hypot(xx - X, yy - Y), 0, 1)[..., None]
                img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - a) + dcol * a
                svg.append(f'<circle cx="{X:.2f}" cy="{Y:.2f}" r="{R:.2f}"/>')
            svg.append("</g>")
        # thread (the six-post grid: post offset c*1080, r*1350 at 1x)
        tcol = CREAM if st == "navy" else NAVY
        canvas = np.zeros((H * 2, W * 2), np.uint8)
        svg.append(f'<g id="thread" fill="none" stroke="rgb({int(tcol[0])},{int(tcol[1])},{int(tcol[2])})" stroke-linecap="round">')
        for k, P in paths.items():
            dd = dash[k]; Q, s = resample(P, 0.25)
            Qp = (Q - [c * 1080, r * 1350]) * K
            if Qp[:, 0].max() < -50 or Qp[:, 0].min() > W + 50 or Qp[:, 1].max() < -50 or Qp[:, 1].min() > H + 50: continue
            on = ((s - dd["phase"]) % dd["period"]) < dd["period"] * dd["duty"]
            e = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
            wpx = dd["width"] * K
            # round caps add the width to each dash: shorten by it so the visible length matches
            for a0, b0 in zip(e[::2], e[1::2]):
                cut = int(round(wpx / 2 / K / 0.25)); a1, b1 = a0 + cut, b0 - cut
                if b1 <= a1 + 1: continue
                seg = Qp[a1:b1]
                cv2.polylines(canvas, [np.int32(np.round(seg * 2 * 16))], False, 255, int(round(wpx * 2)), cv2.LINE_AA, shift=4)
                svg.append(f'<path stroke-width="{wpx:.2f}" d="{svg_path(seg[::8] if len(seg) > 16 else seg)}"/>')
        svg.append("</g></svg>")
        ta = cv2.resize(canvas.astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_AREA)[..., None]
        img = img * (1 - ta) + tcol * ta
        cv2.imwrite(str(OUT / f"{post}_background.png"), cv2.cvtColor(np.clip(img, 0, 255).round().astype(np.uint8), cv2.COLOR_RGB2BGR))
        (OUT / f"{post}_dots_thread.svg").write_text("\n".join(svg))
        # agreement with the approved background where the approved post shows it
        small = cv2.resize(img, (1080, 1350), interpolation=cv2.INTER_AREA)
        vis = fg < 0.05
        d = np.abs(small - approved).max(2)[vis]
        report[post] = dict(dots=len(dots), mean_abs_diff=round(float(d.mean()), 2), p95=round(float(np.percentile(d, 95)), 1))
        print(post, report[post])
    json.dump(report, open(ROOT / "work/psd_assets/background_check.json", "w"), indent=1)

if __name__ == "__main__":
    G = full_plates()
    paths = thread_paths(); dash = {}
    for k, P in paths.items():
        dash[k] = fit_dashes(G, P, None); dash[k]["width"] = measure_width(G, P)
        print(k, {a: round(b, 2) for a, b in dash[k].items()})
    json.dump(dash, open(ROOT / "work/psd_assets/thread_dashes.json", "w"), indent=1)
    render_all(G, paths, dash)
