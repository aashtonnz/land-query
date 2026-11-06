"""Quality checks for one compiled block (T-21, D-12). Writes data/qa.json and prints a one-line summary.

Each check compares two independent sources; it reports agreement, it does not change any value.
1. Council manhole cover levels (NZVD2016) against 2024-25 LiDAR ground at the manhole.
2. Council 2021 building ground heights against LiDAR ground at the building's centre.
3. LiDAR epoch offset: 2024-25 minus 2021 on flat, open, unbuilt ground.
4. Parcel polygon area against LINZ calc_area.
5. LiDAR coverage: share of parcels with no LiDAR cells.
"""
import json, os, sys
import numpy as np, rasterio, duckdb
from rasterio.features import geometry_mask
from shapely.geometry import shape

D = sys.argv[1] if len(sys.argv) > 1 else "data"
RAW = os.path.join(D, "raw")

def feats(n):
    p = os.path.join(RAW, n + ".geojson")
    return [f for f in json.load(open(p))["features"] if f.get("geometry")] if os.path.exists(p) else []

def summary(d):
    d = np.asarray([x for x in d if np.isfinite(x)])
    if d.size == 0: return dict(n=0)
    q = np.percentile(d, [5, 25, 50, 75, 95])
    return dict(n=int(d.size), median=round(float(q[2]), 3), iqr=[round(float(q[1]), 3), round(float(q[3]), 3)],
                p5_p95=[round(float(q[0]), 3), round(float(q[4]), 3)], share_abs_gt_0_5m=round(float((np.abs(d) > 0.5).mean()), 3))

dem = rasterio.open(os.path.join(RAW, "dem_2025.tif")); Z = dem.read(1)
z21 = rasterio.open(os.path.join(RAW, "dem_2021.tif")).read(1)
dsm = rasterio.open(os.path.join(RAW, "dsm_2025.tif")).read(1)

def sample(x, y):
    r, c = dem.index(x, y)
    return float(Z[r, c]) if 0 <= r < Z.shape[0] and 0 <= c < Z.shape[1] else np.nan

qa = {}
mh = [(f["geometry"]["coordinates"], f["properties"].get("cover_level_nzvd2016")) for f in feats("ww_node") + feats("sw_point")
      if f["properties"].get("status") == "INUS" and f["geometry"]["type"] == "Point"]
qa["manhole_cover_minus_lidar_m"] = summary([cl - sample(*xy[:2]) for xy, cl in mh if cl is not None])

bl = [(shape(f["geometry"]).representative_point(), f["properties"].get("Ground")) for f in feats("buildings_2021")]
qa["building_ground_minus_lidar_m"] = summary([gh - sample(p.x, p.y) for p, gh in bl if gh is not None])

gy, gx = np.gradient(Z, 1.0); slope = np.degrees(np.arctan(np.hypot(gx, gy)))
geoms = [shape(f["geometry"]) for f in feats("buildings_2021")]
bmask = ~geometry_mask(geoms, out_shape=Z.shape, transform=dem.transform) if geoms else np.zeros_like(Z, bool)
flat = (slope < 2) & ((dsm - Z) < 0.5) & ~bmask & np.isfinite(Z) & np.isfinite(z21)
dz = (Z - z21)[flat]
if dz.size > 200000: dz = np.random.default_rng(0).choice(dz, 200000, replace=False)
qa["lidar_2025_minus_2021_flat_m"] = summary(dz)

db = duckdb.connect(os.path.join(D, "tile.duckdb"), read_only=True)
raw = {f["properties"]["id"]: f["properties"].get("calc_area") for f in feats("parcels")}
diffs = [a - raw[i] for i, a in db.execute("SELECT unit_id, area_m2 FROM units").fetchall() if raw.get(i) is not None]
qa["parcel_area_minus_linz_calc_m2"] = dict(n=len(diffs), max_abs=round(max(map(abs, diffs)), 2) if diffs else None,
                                            n_abs_gt_1=int(sum(abs(x) > 1 for x in diffs)))
n, nl, partial = db.execute("SELECT count(*), count(*) FILTER (WHERE lidar_cells = 0), count(*) FILTER (WHERE coverage_pct < 99) FROM units").fetchone()
qa["parcels"] = dict(n=n, no_lidar=nl, coverage_lt_99pct=partial)
json.dump(qa, open(os.path.join(D, "qa.json"), "w"), indent=1)
m, b, o = qa["manhole_cover_minus_lidar_m"], qa["building_ground_minus_lidar_m"], qa["lidar_2025_minus_2021_flat_m"]
print(f"QA: manholes {m.get('n')} median {m.get('median')} m; buildings {b.get('n')} median {b.get('median')} m; "
      f"LiDAR offset {o.get('median')} m; area max diff {qa['parcel_area_minus_linz_calc_m2']['max_abs']} m²; "
      f"parcels {n}, no LiDAR {nl}, partial {partial}")
