"""Assemble the six posts from export/photoshop_assets/0X/ (layout.json order, full-canvas
layers, Normal 100%, straight-alpha 'over' compositing at 3240 x 4050, float), export the
3240 x 4050 master and a 1080 x 1350 Instagram PNG (area-average 3:1, exact), the six-post
preview, README.txt and a ZIP; then verify everything.  -> export/final_delivery/"""
import json, zipfile
from pathlib import Path
import cv2, numpy as np
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "export/photoshop_assets"; OUT = ROOT / "export/final_delivery"
OUT.mkdir(parents=True, exist_ok=True)
rep = {}
for n in ["01", "02", "03", "04", "05", "06"]:
    L = json.loads((SRC / n / "layout.json").read_text())
    assert (L["canvas"]["width"], L["canvas"]["height"]) == (3240, 4050)
    comp = None
    for l in sorted(L["layers"], key=lambda x: x["order"]):
        im = cv2.imread(str(SRC / n / l["file"]), cv2.IMREAD_UNCHANGED)
        assert im.shape == (4050, 3240, 4) and (l["x"], l["y"], l["blend"], l["opacity"]) == (0, 0, "normal", 100), l["file"]
        rgb = im[..., 2::-1].astype(np.float32); a = im[..., 3:4].astype(np.float32) / 255
        comp = rgb * a if comp is None else rgb * a + comp * (1 - a)
    m8 = np.clip(comp, 0, 255).round().astype(np.uint8)
    Image.fromarray(m8).save(OUT / f"{n}_master_3240x4050.png", optimize=False, compress_level=6)
    ig = np.clip(cv2.resize(comp, (1080, 1350), interpolation=cv2.INTER_AREA), 0, 255).round().astype(np.uint8)
    Image.fromarray(ig).save(OUT / f"{n}_instagram_1080x1350.png", compress_level=6)
    ref = np.asarray(Image.open(SRC / n / "preview_3240x4050.png").convert("RGB"))
    ref_small = np.asarray(Image.open(SRC / n / "final_1080x1350.png").convert("RGB"))
    rep[n] = dict(master_vs_approved_reconstruction_max_diff=int(np.abs(m8.astype(int) - ref).max()),
                  instagram_vs_approved_reconstruction_max_diff=int(np.abs(ig.astype(int) - ref_small).max()),
                  layers=len(L["layers"]))
    print(n, rep[n])
ims = [np.asarray(Image.open(OUT / f"{n}_instagram_1080x1350.png")) for n in ["01", "02", "03", "04", "05", "06"]]
grid = np.vstack([np.hstack(ims[:3]), np.hstack(ims[3:])])
Image.fromarray(grid).save(OUT / "preview_six_posts.jpg", quality=92)
(OUT / "README.txt").write_text("""JACKETEK - final delivery (6 Instagram posts)

Post in this order (top row first): 01, 02, 03, then 04, 05, 06.

Files
  01_instagram_1080x1350.png ... 06_instagram_1080x1350.png
      Ready to post. 1080 x 1350 px (4:5), PNG, sRGB. Open on any phone or computer.
  01_master_3240x4050.png ... 06_master_3240x4050.png
      High-resolution masters, 3240 x 4050 px (3x), assembled from the separated
      layers in export/photoshop_assets/0X/ (layout.json order, Normal 100%).
      The Instagram files are these masters reduced exactly 3:1 (area average).
  preview_six_posts.jpg
      All six posts together, as on the profile.
  jacketek_final_delivery.zip
      All of the above in one archive.

Quality note
  Posts 04-06 carry real 3x detail (full-resolution jacket photos, vector type,
  vector frames, dots and thread). Posts 01-03 come from a 667 x 888 px source per
  post: their masters are clean at 3x but hold no detail beyond that source.
  Nothing was invented by upscaling. See export/photoshop_assets/SOURCE_QUALITY_REPORT.md.
""")
zp = OUT / "jacketek_final_delivery.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.glob("*_*.png")) + [OUT / "preview_six_posts.jpg", OUT / "README.txt"]:
        z.write(f, f.name)
# verify: every PNG in the ZIP decodes, with the right size
with zipfile.ZipFile(zp) as z:
    assert z.testzip() is None
    names = z.namelist(); pngs = [x for x in names if x.endswith(".png")]
    import io
    for x in pngs:
        im = Image.open(io.BytesIO(z.read(x))); im.load()
        want = (3240, 4050) if "master" in x else (1080, 1350)
        assert im.size == want and im.mode == "RGB", (x, im.size, im.mode)
    Image.open(io.BytesIO(z.read("preview_six_posts.jpg"))).load()
rep["zip"] = dict(file=zp.name, entries=len(names), png_decoded=len(pngs), size_mb=round(zp.stat().st_size / 1e6, 1))
print(rep["zip"])
(OUT / "verification.json").write_text(json.dumps(rep, indent=1))
