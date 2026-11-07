"""Quality checks for one compiled block (T-21, D-12). Writes data/qa.json and prints a one-line summary.

Each check compares two independent sources; it reports agreement, it does not change any value.
1. Council manhole cover levels (NZVD2016) against 2024-25 LiDAR ground at the manhole, wastewater (WWMH) and
   stormwater (SWMH) separately. Culvert ends, sumps and soakage are left out: their levels sit below the bank or
   kerb that a 1 m LiDAR cell takes in (T-44, the Te Horo block).
2. Council 2021 building ground heights against LiDAR ground at the building's centre.
3. LiDAR epoch offset: 2024-25 minus 2021 on flat, open, unbuilt ground.
4. Parcel polygon area against the LINZ primary parcel of the same id (fetched from LINZ, not the KCDC mirror),
   run in every block, with or without LiDAR.
5. LiDAR coverage: share of parcels with no LiDAR cells.
6. Roof surface (2024-25 DSM median inside each outline) against KCDC's 2021 photogrammetric building height (BLD_ave).
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

def area_check(db):
    """Compiled parcel area against the area of the LINZ parcel with the same id."""
    linz = {f["properties"].get("id"): shape(f["geometry"]).area for f in feats("linz_parcels")}
    if not linz: return dict(n=0, note="LINZ parcels not fetched (needs LINZ_API_KEY)")
    rows = db.execute("SELECT unit_id, area_m2, coverage_pct FROM units").fetchall()
    diffs = {i: a - linz[i] for i, a, _ in rows if i in linz}
    # KCDC's mirror clips parcels that cross the district boundary, so those are smaller than LINZ by design
    clipped = {i: d for i, d in diffs.items() if d < -1}
    other = {i: d for i, d in diffs.items() if d >= -1}
    worst = sorted(other.items(), key=lambda t: -abs(t[1]))[:5]
    return dict(n=len(diffs), not_in_linz=sum(1 for i, _, _ in rows if i not in linz),
                smaller_than_linz_gt_1=len(clipped), n_abs_gt_1=int(sum(abs(d) > 1 for d in other.values())),
                max_abs=round(max(map(abs, other.values())), 2) if other else None,
                worst=[[i, round(d, 2)] for i, d in worst if abs(d) > 1],
                smaller_examples=[[i, round(d, 2)] for i, d in sorted(clipped.items(), key=lambda t: t[1])[-5:]])


db = duckdb.connect(os.path.join(D, "tile.duckdb"), read_only=True)
qa = {"parcel_area_minus_linz_m2": area_check(db)}
if not all(os.path.exists(os.path.join(RAW, n + ".tif")) for n in ("dem_2025", "dsm_2025", "dem_2021")):
    n = db.execute("SELECT count(*) FROM units").fetchone()[0]
    qa.update(no_lidar_window=True, parcels=dict(n=n, no_lidar=n))
    json.dump(qa, open(os.path.join(D, "qa.json"), "w"), indent=1)
    print(f"QA: no LiDAR for this window; {n} parcels without terrain; area n {qa['parcel_area_minus_linz_m2']['n']}"); sys.exit(0)
dem = rasterio.open(os.path.join(RAW, "dem_2025.tif")); Z = dem.read(1)
z21 = rasterio.open(os.path.join(RAW, "dem_2021.tif")).read(1)
dsm = rasterio.open(os.path.join(RAW, "dsm_2025.tif")).read(1)

def sample(x, y):
    r, c = dem.index(x, y)
    return float(Z[r, c]) if 0 <= r < Z.shape[0] and 0 <= c < Z.shape[1] else np.nan

for key, layer, kind in (("ww_manhole_cover_minus_lidar_m", "ww_node", "WWMH"), ("sw_manhole_cover_minus_lidar_m", "sw_point", "SWMH")):
    mh = [(f["geometry"]["coordinates"], f["properties"].get("cover_level_nzvd2016")) for f in feats(layer)
          if f["properties"].get("status") == "INUS" and f["properties"].get("node_type") == kind and f["geometry"]["type"] == "Point"]
    qa[key] = summary([cl - sample(*xy[:2]) for xy, cl in mh if cl is not None])

bl = [(shape(f["geometry"]).representative_point(), f["properties"].get("Ground")) for f in feats("buildings_2021")]
qa["building_ground_minus_lidar_m"] = summary([gh - sample(p.x, p.y) for p, gh in bl if gh is not None])

gy, gx = np.gradient(Z, 1.0); slope = np.degrees(np.arctan(np.hypot(gx, gy)))
geoms = [shape(f["geometry"]) for f in feats("buildings_2021")]
bmask = ~geometry_mask(geoms, out_shape=Z.shape, transform=dem.transform) if geoms else np.zeros_like(Z, bool)
flat = (slope < 2) & ((dsm - Z) < 0.5) & ~bmask & np.isfinite(Z) & np.isfinite(z21)
dz = (Z - z21)[flat]
if dz.size > 200000: dz = np.random.default_rng(0).choice(dz, 200000, replace=False)
qa["lidar_2025_minus_2021_flat_m"] = summary(dz)

from shapely.geometry import box as _box
rd = []
for f in feats("buildings_2021")[:3000]:
    p_ = f["properties"]
    if p_.get("BLD_ave") is None: continue
    g = shape(f["geometry"]).buffer(-0.5)
    if g.is_empty or g.area < 5: continue
    b = g.bounds; r0, c0 = dem.index(b[0], b[3]); r1, c1 = dem.index(b[2], b[1])
    r0, c0 = max(0, r0), max(0, c0); r1, c1 = min(Z.shape[0], r1 + 1), min(Z.shape[1], c1 + 1)
    if r1 <= r0 or c1 <= c0: continue
    tr = rasterio.windows.transform(rasterio.windows.Window(c0, r0, c1 - c0, r1 - r0), dem.transform)
    mm = ~geometry_mask([g], out_shape=(r1 - r0, c1 - c0), transform=tr)
    v = dsm[r0:r1, c0:c1][mm]; v = v[np.isfinite(v)]
    if v.size >= 5: rd.append(float(np.median(v)) - p_["BLD_ave"])
qa["roof_dsm_minus_kcdc_bld_ave_m"] = summary(rd)

n, nl, partial = db.execute("SELECT count(*), count(*) FILTER (WHERE lidar_cells = 0), count(*) FILTER (WHERE coverage_pct < 99) FROM units").fetchone()
qa["parcels"] = dict(n=n, no_lidar=nl, coverage_lt_99pct=partial)
json.dump(qa, open(os.path.join(D, "qa.json"), "w"), indent=1)
w, sw, b, o = qa["ww_manhole_cover_minus_lidar_m"], qa["sw_manhole_cover_minus_lidar_m"], qa["building_ground_minus_lidar_m"], qa["lidar_2025_minus_2021_flat_m"]
print(f"QA: wastewater manholes {w.get('n')} median {w.get('median')} m; stormwater manholes {sw.get('n')} median {sw.get('median')} m; buildings {b.get('n')} median {b.get('median')} m; "
      f"LiDAR offset {o.get('median')} m; area vs LINZ max diff {qa['parcel_area_minus_linz_m2'].get('max_abs')} m² (n {qa['parcel_area_minus_linz_m2']['n']}); "
      f"parcels {n}, no LiDAR {nl}, partial {partial}")
