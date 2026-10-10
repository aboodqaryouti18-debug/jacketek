"""Add the two new background layers to the latest six posts (nothing else changes):
  dots    one grid for the whole six-post composition (G coordinates: same spacing and
          phase across every boundary), tone-on-tone: navy x1.45 (a lighter navy, ~7%),
          beige x0.92 (a darker beige, ~8%)
  thread  the one continuous path (work/thread/path.json), dashed by its own arclength,
          so the dashes run on across the boundaries; cream #FCF0D6 on the navy posts,
          navy #003049 on the beige posts (the colour switches exactly at the boundary)
Both are applied to background pixels only (work/thread/POST_0X_fg.png = content): the
thread passes behind prints, stickers and type, never over them.
Inputs : export/posts01-03_striped_1080x1350, export/rebuild_1080x1350 (untouched)
Output : export/six_posts_thread_v2/POST_0X.png + profile grid + layers"""
import json, sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/thread"))
import layout as L
from masks import FINAL
W = ROOT / "work/thread"; OUT = ROOT / "export/six_posts_thread_v2"
# measured on the reference (source/reference_dots_thread.jpg, scaled to post px):
# a sparse dot grid every ~72 px, small dots; long dashes on broad curves
DOT_STEP, DOT_R = 72.0, 1.9
# tone-on-tone, palette colours only: cream at 30% on navy, navy at 24% on beige (small dots: a subtle grid overall)
DOT_MIX = {"navy": ((0xFC, 0xF0, 0xD6), 0.30), "beige": ((0x00, 0x30, 0x49), 0.24)}
THREAD = {"navy": (0xFC, 0xF0, 0xD6), "beige": (0x00, 0x30, 0x49)}
DASH_ON, DASH_OFF, WIDTH_X3, OPACITY = 22.0, 13.0, 9, 0.92    # width 9 px at 3x = 3 px
SSX = 3

def dots_alpha(post):
    dx, dy = L.offset(post)
    yy, xx = np.mgrid[0:1350, 0:1080].astype(np.float32)
    gx, gy = xx + 0.5 + dx, yy + 0.5 + dy
    fx = (gx - DOT_STEP / 2) % DOT_STEP; fx = np.minimum(fx, DOT_STEP - fx)
    fy = (gy - DOT_STEP / 2) % DOT_STEP; fy = np.minimum(fy, DOT_STEP - fy)
    d = np.hypot(fx, fy)
    return np.clip(DOT_R + 0.5 - d, 0, 1)

def thread_alpha(post, P, s):
    dx, dy = L.offset(post)
    canvas = np.zeros((1350 * SSX, 1080 * SSX), np.uint8)
    on = (s % (DASH_ON + DASH_OFF)) < DASH_ON
    # dash runs
    edges = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
    for a, b in zip(edges[::2], edges[1::2]):
        seg = (P[a:b] - [dx, dy]) * SSX
        if seg[:, 0].max() < -20 or seg[:, 0].min() > 1080 * SSX + 20 or seg[:, 1].max() < -20 or seg[:, 1].min() > 1350 * SSX + 20:
            continue
        cv2.polylines(canvas, [np.int32(np.round(seg * 4))], False, 255, WIDTH_X3, cv2.LINE_AA, shift=2)
    return cv2.resize(canvas.astype(np.float32) / 255, (1080, 1350), interpolation=cv2.INTER_AREA)

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    P = np.array(json.loads((W / "path.json").read_text())["points"])
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    report = {}
    for post in L.POS:
        style = L.STYLE[post]
        img = cv2.cvtColor(cv2.imread(str(FINAL[post])), cv2.COLOR_BGR2RGB).astype(np.float32)
        fg = cv2.imread(str(W / f"{post}_fg.png"), 0).astype(np.float32) / 255
        bgw = 1 - np.clip(cv2.GaussianBlur(cv2.dilate(fg, np.ones((3, 3))), (0, 0), 0.8), 0, 1)
        bgw_t = 1 - np.clip(cv2.GaussianBlur(cv2.dilate(fg, np.ones((7, 7))), (0, 0), 1.0), 0, 1)   # thread: a clean gap at content
        strict = (fg < 0.3).astype(np.float32)        # content pixels stay bit-identical
        bgw *= strict; bgw_t *= strict
        da = dots_alpha(post) * bgw
        dc, dk = DOT_MIX[style]
        dw = (da * dk)[..., None]
        out = img * (1 - dw) + np.float32(dc) * dw
        ta = thread_alpha(post, P, s) * bgw_t * OPACITY
        out = out * (1 - ta[..., None]) + np.float32(THREAD[style]) * ta[..., None]
        o8 = np.clip(out, 0, 255).round().astype(np.uint8)
        cv2.imwrite(str(OUT / f"{post}.png"), cv2.cvtColor(o8, cv2.COLOR_RGB2BGR))
        cv2.imwrite(str(W / f"{post}_layer_dots.png"), (da * 255).round().astype(np.uint8))
        cv2.imwrite(str(W / f"{post}_layer_thread.png"), (ta * 255).round().astype(np.uint8))
        ch = np.abs(o8.astype(int) - img.round().astype(int)).max(2) > 0
        report[post] = dict(style=style, changed_px=int(ch.sum()), changed_on_content_px=int((ch & (fg > 0.5)).sum()),
                            thread_px=int((ta > 0.05).sum()))
    # the profile grid (centre 3:4 of each post) and the full posts
    row = lambda ps: np.hstack([cv2.imread(str(OUT / f"{p}.png"))[:, int(round(L.ox(p))):int(round(L.ox(p))) + int(round(L.PW[p] * L.S))] for p in ps])
    a, b = row(["POST_01", "POST_02", "POST_03"]), row(["POST_04", "POST_05", "POST_06"])
    w = min(a.shape[1], b.shape[1])
    cv2.imwrite(str(OUT / "profile_grid.png"), np.vstack([a[:, :w], b[:, :w]]))
    full = [cv2.imread(str(OUT / f"{p}.png")) for p in L.POS]
    cv2.imwrite(str(OUT / "six_posts_full.jpg"), np.vstack([np.hstack(full[:3]), np.hstack(full[3:])]), [cv2.IMWRITE_JPEG_QUALITY, 92])
    (OUT / "report.json").write_text(json.dumps(report, indent=1)); print(json.dumps(report, indent=1))
