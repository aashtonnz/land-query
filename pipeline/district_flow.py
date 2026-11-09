"""District-scale overland flow (T-42): upslope area on a 10 m mosaic covering whole catchments.

Per-block flow on the 1 m LiDAR stops at the block's fetch window, so a parcel beside the Waikanae or Ōtaki River
sees only the part of its catchment inside that window. This builds one elevation mosaic over the district and the
hills that drain into it (to the Tararua divide), from LINZ's national 1 m DEM read at 10 m, with gaps filled from
LINZ's national contour-interpolated 8 m DEM, and computes D8 upslope area on it. Cells whose upslope area reaches
the mosaic edge are flagged as truncated.

Usage: district_flow.py OUT_TIF [xmin,ymin,xmax,ymax]. Writes a four-band GeoTIFF (1 upslope area m², 2 truncated
0/1, 3 mean ground within ±500 m with the sea at 0 m, 4 ground m) and OUT_TIF.json with provenance.
"""
import hashlib, json, sys, time
import numpy as np, rasterio, requests
from rasterio.transform import from_origin
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
import measures as M
from scipy.ndimage import uniform_filter
from provenance import utc_now

# district blocks span 1755000-1805000 E, 5455000-5495000 N; the mosaic extends east and south-east to the
# Tararua divide so the Ōtaki, Waikanae and smaller catchments are whole (checked by the truncation flag)
from councils import COUNCIL as C
BBOX = tuple(int(v) for v in (sys.argv[2].split(",") if __name__ == "__main__" and len(sys.argv) > 2 else C.FLOW_BBOX))
RES = 10.0
OUT_BBOX = C.FLOW_OUT_BBOX  # district blocks plus 3 km: every block's LiDAR window
BASE = "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/new-zealand/"
COLLS = [("new-zealand/dem_1m/2193", "LINZ national 1 m DEM"), ("new-zealand-contour/dem_8m/2193", "LINZ contour-interpolated 8 m DEM")]


ROWS = [a + b for a in "ABC" for b in "ABCDEFGHJKLMNPQRSTUVWXYZ"]  # Topo50 row codes skip I and O


def topo50_candidates(bbox=None):
    """Topo50 sheets (24 km wide, 36 km tall; BN32 spans 1756000-1780000 E, 5478000-5514000 N) touching bbox."""
    BBOX = bbox or globals()["BBOX"]
    out = []
    for i, rc in enumerate(ROWS):
        top = 5514000 - (i - ROWS.index("BN")) * 36000
        for col in range(1, 50):
            left = 1756000 + (col - 32) * 24000
            if left < BBOX[2] and left + 24000 > BBOX[0] and top > BBOX[1] and top - 36000 < BBOX[3]:
                out.append(f"{rc}{col:02d}")
    return out


def get(url, **kw):
    for k in range(5):
        try:
            r = requests.get(url, timeout=60, **kw)
            if r.status_code == 404: return None
            r.raise_for_status(); return r
        except requests.RequestException:
            if k == 4: raise
            time.sleep(2 ** k)


def sheets(coll, bbox=None):
    """Sheets of the collection whose real bounds (read from the file) intersect bbox (default BBOX)."""
    BBOX = bbox or globals()["BBOX"]
    c = get(BASE + coll + "/collection.json").json()
    hits = []
    for code in topo50_candidates(BBOX):
        if not get(BASE + coll + f"/{code}.json"): continue  # no sheet there (sea)
        h = BASE + coll + f"/{code}.tiff"
        with rasterio.open("/vsicurl/" + h) as d:
            b = d.bounds
        if b.left < BBOX[2] and b.right > BBOX[0] and b.bottom < BBOX[3] and b.top > BBOX[1]: hits.append(h)
    return c, hits


def mosaic(bbox=None, res=None, lidar_mask=False):
    """(ground, transform, provenance), or with lidar_mask also a mask of cells whose ground is from the 1 m LiDAR DEM."""
    BBOX, RES = bbox or globals()["BBOX"], res or globals()["RES"]
    W, H = int((BBOX[2] - BBOX[0]) / RES), int((BBOX[3] - BBOX[1]) / RES)
    T = from_origin(BBOX[0], BBOX[3], RES, RES)
    Z = np.full((H, W), np.nan, np.float32)
    Z8 = np.full((H, W), np.nan, np.float32)  # the 8 m contour DEM alone: it has no data over the sea
    prov = []
    for coll, title in COLLS:
        c, hrefs = sheets(coll, BBOX)
        for h in hrefs:
            with rasterio.open("/vsicurl/" + h) as src:
                # the part of the mosaic this sheet covers, read at 10 m (GDAL uses the file's overviews)
                x0, y0 = max(BBOX[0], src.bounds.left), max(BBOX[1], src.bounds.bottom)
                x1, y1 = min(BBOX[2], src.bounds.right), min(BBOX[3], src.bounds.top)
                if x1 <= x0 or y1 <= y0: continue
                c0, r0 = int((x0 - BBOX[0]) / RES), int((BBOX[3] - y1) / RES)
                w, hgt = int(round((x1 - x0) / RES)), int(round((y1 - y0) / RES))
                part = src.read(1, window=from_bounds(x0, y0, x1, y1, src.transform), out_shape=(hgt, w),
                                resampling=Resampling.average, masked=True).filled(np.nan).astype(np.float32)
            dst = Z[r0:r0 + hgt, c0:c0 + w]
            fill = np.isnan(dst) & np.isfinite(part); dst[fill] = part[fill]
            if "contour" in coll: Z8[r0:r0 + hgt, c0:c0 + w] = np.where(np.isfinite(part), part, Z8[r0:r0 + hgt, c0:c0 + w])
        prov.append(dict(collection=BASE + coll + "/collection.json", title=c.get("title"), items=hrefs,
                         licence=c.get("license"), fetched=utc_now()))
        if lidar_mask and "contour" not in coll: L = np.isfinite(Z)
    from lidar_catalogue import NO_DATA_FLOOR
    Z[Z <= NO_DATA_FLOOR] = np.nan   # a real height can be below -100 m (T-112)
    Z[sea_mask(Z, Z8)] = np.nan
    return (Z, T, prov, L & np.isfinite(Z)) if lidar_mask else (Z, T, prov)


def sea_mask(Z, Z8, max_m=0.5):
    """The sea: the national 1 m DEM stores it as a flat surface (-0.56 m off Kāpiti, -1.005 m further north) rather
    than as no data, so it is taken as cells with no 8 m contour DEM value and no higher than max_m (T-47)."""
    return np.isnan(Z8) & np.isfinite(Z) & (Z <= max_m)


def mean_ground(Z, res, half_m=500):
    """Mean ground within ±half_m (a square), counting the sea and other no-data cells at 0 m."""
    return uniform_filter(np.where(np.isfinite(Z), Z, 0).astype(np.float32), int(round(2 * half_m / res)) + 1, mode="nearest")


if __name__ == "__main__":
    t0 = time.time(); out = sys.argv[1]
    Z, T, prov = mosaic(); print(f"mosaic {Z.shape} valid {np.isfinite(Z).mean():.3f} in {time.time()-t0:.0f}s")
    edge = np.zeros(Z.shape, bool); edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True  # the sea is an outlet
    ACC, TR, _ = M.flow_routing(Z, T, inflow=edge)
    MEAN500 = mean_ground(Z, RES)
    # write only the district and a margin covering every block's LiDAR window, at the precision the compiler uses
    c0, r0 = int((OUT_BBOX[0] - BBOX[0]) / RES), int((BBOX[3] - OUT_BBOX[3]) / RES)
    c1, r1 = int((OUT_BBOX[2] - BBOX[0]) / RES), int((BBOX[3] - OUT_BBOX[1]) / RES)
    crop = lambda a: a[r0:r1, c0:c1]
    bands = [np.round(crop(ACC)), crop(TR).astype(np.float32), np.round(crop(MEAN500), 2), np.round(crop(Z), 1)]
    with rasterio.open(out, "w", driver="GTiff", height=r1 - r0, width=c1 - c0, count=4, dtype="float32",
                       crs="EPSG:2193", transform=from_origin(OUT_BBOX[0], OUT_BBOX[3], RES, RES), nodata=np.nan,
                       compress="zstd", predictor=3, tiled=True) as d:
        for i, (n, a) in enumerate(zip(("upslope_area_m2", "upslope_truncated", "mean_ground_500m_sea0_m", "ground_m"), bands), 1):
            d.write(a, i); d.set_band_description(i, n)
    meta = dict(bbox=BBOX, written_bbox=OUT_BBOX, res_m=RES, sources=prov, sha256=hashlib.sha256(ACC.tobytes()).hexdigest(), fetched=utc_now(),
                max_upslope_km2=round(float(np.nanmax(ACC)) / 1e6, 1), seconds=round(time.time() - t0))
    json.dump(meta, open(out + ".json", "w"), indent=1)
    print(json.dumps({k: v for k, v in meta.items() if k != "sources"}))
