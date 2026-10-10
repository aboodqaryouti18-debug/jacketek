"""The reference grid's background (posts 01-03, source/embroidery_reference_posts01-03.webp),
measured for posts 04-06:
  beige (post 02)   peak colour + its light: an elliptical fall-off and a floor fall-off
                    (least squares on clean background pixels: away from prints, shadows, type;
                    the photos cover the panel's centre, so a smooth physical model, not a free fit)
  navy (01, 03)     flat colour (median); its light variation is < 1%
-> work/rebuild/ref_background.json"""
import json
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]

def light(q, u, v):
    """peak x elliptical fall-off x floor fall-off (the bottom of the panel darkens)"""
    P, au, av, vc, fl, v0 = q
    f = np.clip((v - v0) / (1 - v0), 0, 1)
    return P * (1 - au * ((u - 0.5) / 0.5) ** 2 - av * ((v - vc) / 0.5) ** 2) * (1 - fl * f * f)

if __name__ == "__main__":
    a = cv2.cvtColor(cv2.imread(str(ROOT / "source/embroidery_reference_posts01-03.webp")), cv2.COLOR_BGR2RGB).astype(np.float64)
    out = {}
    # navy: posts 01 and 03
    nav = np.concatenate([a[:, 2:665].reshape(-1, 3), a[:, 1335:1998].reshape(-1, 3)])
    nav = nav[(np.abs(nav - [0, 47, 71]).max(1) < 6)]
    out["navy"] = dict(colour=np.median(nav, 0).round(2).tolist(), n=int(len(nav)))
    # beige: post 02
    p = a[:, 668:1332]; H, W = p.shape[:2]
    lum = p @ [0.299, 0.587, 0.114]
    rb, gb = p[..., 0] - p[..., 2], p[..., 1] - p[..., 2]   # beige: R-B 29..38, G-B 22..26 (cooler at the floor)
    beige = (rb > 22) & (rb < 46) & (gb > 15) & (gb < 33) & (lum > 195) & (lum < 245)
    smooth = np.abs(lum - cv2.GaussianBlur(lum, (0, 0), 2)) < 1.5
    clean = beige & smooth
    # away from anything that is not background (prints, their shadows, type): 9 px
    clean = cv2.erode(clean.astype(np.uint8), np.ones((19, 19))) > 0
    clean[:4] = clean[-2:] = False
    ys, xs = np.nonzero(clean)
    u = (xs + 0.5) / W; v = (ys + 0.5) / H
    y = lum[ys, xs]
    from scipy.optimize import least_squares
    keep = np.ones(len(y), bool)
    for _ in range(3):
        fit = least_squares(lambda q: light(q, u[keep], v[keep]) - y[keep], [240, 0.06, 0.06, 0.5, 0.12, 0.8],
                            bounds=([200, 0, 0, 0.2, 0, 0.5], [255, 0.5, 0.5, 0.8, 0.4, 0.97]))
        r = y - light(fit.x, u, v); keep = np.abs(r) < max(1.0, 2.5 * np.std(r[keep]))
    q = fit.x
    yy, xx = np.mgrid[0:H, 0:W]
    model = light(q, (xx + 0.5) / W, (yy + 0.5) / H)
    peak = q[0]
    # the colour at the light's peak: the background pixels within 1% of it
    near = np.abs(y / light(q, u, v) - 1) < 0.01
    ratio = p[ys, xs][near] / (light(q, u, v)[near, None] / peak)
    peak_rgb = np.median(ratio, 0)
    out["beige"] = dict(peak_colour=peak_rgb.round(2).tolist(), params=dict(zip(["peak", "a_u", "a_v", "v_centre", "floor", "floor_from"], [float(x) for x in q])),
                        rms=float(np.std(r[keep])), n=int(keep.sum()),
                        gain_corners=[round(float(model[0, 0] / peak), 4), round(float(model[0, -1] / peak), 4),
                                      round(float(model[-1, 0] / peak), 4), round(float(model[-1, -1] / peak), 4)],
                        gain_centre=round(float(model[H // 2, W // 2] / peak), 4))
    print(json.dumps(out, indent=1))
    (ROOT / "work/rebuild/ref_background.json").write_text(json.dumps(out, indent=1))
    vis = np.clip(model / peak * 255, 0, 255).astype(np.uint8)
    m = (clean * 255).astype(np.uint8)
    cv2.imwrite("/tmp/claude-0/-home-user/0c8a008e-acb8-50fa-b850-2737be83dd04/scratchpad/refgain.png", np.hstack([vis, m]))
