"""Side-by-side 2021 and 2025 aerials of parcels, for checking LiDAR ground-change candidates by eye (T-29).

LINZ 7.5 cm Kāpiti Coast aerial photography, 2021 and 2025 (CC BY 4.0; LINZ, AAM NZ, Aerial Surveys, KCDC), read
from the public nz-imagery bucket at about 0.3 m. The parcel outline (KCDC mirror geometry, for drawing) is overlaid.
Usage: aerial_pairs.py OUT_DIR UNIT_ID[:caption] ...   Writes OUT_DIR/<unit_id>.png.
"""
import os, sys
import numpy as np, rasterio, requests
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from PIL import Image, ImageDraw
from shapely.geometry import shape

B = "https://nz-imagery.s3.ap-southeast-2.amazonaws.com/wellington/"
SETS = {"2021": ("kapiti-coast_2021_0.075m", 500, 240, 360), "2025": ("kapiti-coast_2025_0.075m", 1000, 480, 720)}
ROWS = [a + b for a in "ABC" for b in "ABCDEFGHJKLMNPQRSTUVWXYZ"]  # Topo50 row codes skip I and O
RES = 0.3
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")


def tiles(x0, y0, x1, y1, scale, w, h):
    """Topo50 1:500 or 1:1000 tile codes covering the box: SHEET_SCALE_rrrccc (row then column, from the sheet's top left)."""
    out = set()
    for x in np.arange(x0, x1 + w, w / 2):
        for y in np.arange(y0, y1 + h, h / 2):
            x_, y_ = min(x, x1), min(y, y1)
            col = 32 + int((x_ - 1756000) // 24000); row = ROWS.index("BN") + int((5514000 - y_) // 36000)
            left = 1756000 + (col - 32) * 24000; top = 5514000 - (row - ROWS.index("BN")) * 36000
            c, r = int((x_ - left) // w) + 1, int((top - y_) // h) + 1
            out.add(f"{ROWS[row]}{col:02d}_{scale}_{r:03d}{c:03d}" if scale == 500 else f"{ROWS[row]}{col:02d}_{scale}_{r:02d}{c:02d}")
    return sorted(out)


def read(year, box):
    coll, scale, w, h = SETS[year]
    x0, y0, x1, y1 = box
    W, H = int((x1 - x0) / RES), int((y1 - y0) / RES)
    img = np.zeros((3, H, W), np.uint8)
    for t in tiles(x0, y0, x1, y1, scale, w, h):
        try:
            with rasterio.open(f"/vsicurl/{B}{coll}/rgb/2193/{t}.tiff") as d:
                b = d.bounds
                ix0, iy0, ix1, iy1 = max(x0, b.left), max(y0, b.bottom), min(x1, b.right), min(y1, b.top)
                if ix1 <= ix0 or iy1 <= iy0: continue
                c0, r0 = int((ix0 - x0) / RES), int((y1 - iy1) / RES)
                cw, rh = max(1, int(round((ix1 - ix0) / RES))), max(1, int(round((iy1 - iy0) / RES)))
                part = d.read([1, 2, 3], window=from_bounds(ix0, iy0, ix1, iy1, d.transform), out_shape=(3, rh, cw),
                              resampling=Resampling.average)
                img[:, r0:r0 + rh, c0:c0 + cw] = part[:, :H - r0, :W - c0]
        except rasterio.errors.RasterioIOError:
            continue  # no tile there (sea, or outside the flight)
    return Image.fromarray(np.moveaxis(img, 0, -1))


def parcel(uid):
    j = requests.get("https://maps.kapiticoast.govt.nz/server/rest/services/Public/Cadastral/MapServer/0/query",
                     params=dict(where=f"id={uid}", outFields="appellation", outSR=2193, f="geojson"), timeout=60).json()
    f = j["features"][0]
    return shape(f["geometry"]), f["properties"]["appellation"]


def pair(uid, out, caption=""):
    g, app = parcel(uid)
    x0, y0, x1, y1 = g.bounds; m = max(15, 0.15 * max(x1 - x0, y1 - y0))
    box = (x0 - m, y0 - m, x1 + m, y1 + m)
    panels = []
    for year in ("2021", "2025"):
        im = read(year, box); dr = ImageDraw.Draw(im)
        for poly in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            pts = [((x - box[0]) / RES, (box[3] - y) / RES) for x, y in poly.exterior.coords]
            dr.line(pts, fill=(255, 40, 40), width=3)
        dr.rectangle([0, 0, 70, 22], fill=(0, 0, 0)); dr.text((6, 5), year, fill=(255, 255, 255))
        panels.append(im)
    W, H = panels[0].size
    canvas = Image.new("RGB", (2 * W + 10, H + 30), (255, 255, 255))
    canvas.paste(panels[0], (0, 30)); canvas.paste(panels[1], (W + 10, 30))
    ImageDraw.Draw(canvas).text((6, 8), f"{uid}  {app}  {caption}", fill=(0, 0, 0))
    scale = min(1.0, 1400 / canvas.size[0]); canvas = canvas.resize((int(canvas.size[0] * scale), int(canvas.size[1] * scale)))
    canvas.save(os.path.join(out, f"{uid}.png"))


if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for a in sys.argv[2:]:
        uid, _, cap = a.partition(":")
        try: pair(int(uid), out, cap); print("ok", uid)
        except Exception as e: print("FAILED", uid, e)
