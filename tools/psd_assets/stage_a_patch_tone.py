"""Stage A (1080 px, the approved pipeline): the light that tints each patch in posts 04-06
(compose.patches_layer: tone from the approved composite's blurred luminance, sigma 30*S).
It is a very smooth field, so it is computed here exactly as approved and enlarged in stage B.
-> work/psd_assets/tone_POST_0X_<patch>.npy"""
import sys
from pathlib import Path
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/newbg"))
import replace_photos_l as RPL          # installs the burgundy photos into compose
RB = RPL.RB; C = RB.C
sys.path.insert(0, str(ROOT / "tools/patches")); import composite as pc
grain = cv2.cvtColor(cv2.imread("/home/user/jacketportable/public/assets/texture/grain-soft-240.png", cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA).astype(np.float32)
LUMW = np.float32([0.2126, 0.7152, 0.0722])
for post in ("POST_04", "POST_05", "POST_06"):
    w, _ = C.background(post, grain); d_rgb, d_a = C.dashes_layer(post)
    light_img = C.text_layers(post, C.prints_layers(post, C.over(w, d_rgb, d_a)))
    light = cv2.GaussianBlur(light_img @ LUMW, (0, 0), 30 * C.S)
    for n, c, D, rot, kind in C.PATCH_PLACE.get(post, pc.PLACE[post]):
        t, sh = pc.load(n)
        M = C.to_out(pc.matrix(t[..., 3], c, D, rot), post, C.SS)
        a = C.down(cv2.warpAffine(t[..., 3], M, (C.W_OUT * C.SS, C.H_OUT * C.SS), flags=cv2.INTER_LINEAR))
        refl = np.median(light[a > 0.5])
        tone = np.clip(1 + (light / max(refl, 1e-3) - 1) * 0.35, 0.92, 1.05).astype(np.float32)
        np.save(ROOT / f"work/psd_assets/tone_{post}_{n}.npy", tone); print(post, n, kind, round(float(refl), 1))
