"""Compile per-unit raw primitives for the live tile into DuckDB.

Unit = LINZ parcel if data/raw/parcels.geojson exists, otherwise KCDC building outline (stand-in,
labelled as such). Every column group names its source key in provenance.json. No scores,
no opinions: overlaps, distances, elevations and the raw attributes of the nearest assets.
"""
import json, os, sys, time, math
import numpy as np, duckdb, rasterio
from rasterio.features import geometry_mask
from shapely.geometry import shape, Point, box
from shapely.strtree import STRtree
from shapely.ops import unary_union

D = sys.argv[1] if len(sys.argv) > 1 else "data"
RAW = os.path.join(D, "raw")
t0 = time.time()
TILE_BOX = box(1769000, 5468400, 1770000, 5469400)

def load(name):
    p = os.path.join(RAW, name + ".geojson")
    if not os.path.exists(p): return []
    out = []
    for f in json.load(open(p))["features"]:
        if f.get("geometry"):
            g = shape(f["geometry"])
            if not g.is_valid: g = g.buffer(0)
            out.append((g, f["properties"]))
    return out

unit_src = "parcels" if os.path.exists(os.path.join(RAW, "parcels.geojson")) else "buildings_2021"
units = load(unit_src)
print("unit source:", unit_src, len(units))

poly_layers = ["zones", "ovl_flood_hazard", "ovl_ecological_sites", "ovl_noise_corridor", "ovl_coastal_env",
               "flood_stream_corridor", "flood_overflow_path", "flood_storage", "flood_ponding",
               "wind_stainless", "wind_very_high", "tsunami_zones", "ovl_fault_avoidance",
               "gw_liquefaction", "gw_eq_slope_failure"]
point_layers = ["ovl_heritage_places", "ovl_notable_trees"]
L = {n: load(n) for n in poly_layers + point_layers}
trees = {n: STRtree([g for g, _ in v]) for n, v in L.items() if v}

ww_nodes = [(g, p) for g, p in load("ww_node") if p.get("invert_level_nzvd2016") is not None]
sw_nodes = [(g, p) for g, p in load("sw_point") if p.get("invert_level_nzvd2016") is not None]
ww_pipes = load("ww_pipe"); ws_pipes = load("ws_pipe")
rbl = load("flood_rbl_nzvd2016")
T = {k: STRtree([g for g, _ in v]) for k, v in dict(ww_nodes=ww_nodes, sw_nodes=sw_nodes, ww_pipes=ww_pipes,
                                                    ws_pipes=ws_pipes, rbl=rbl).items() if v}
bld_union = unary_union([g for g, _ in load("buildings_2021")])

dem = rasterio.open(os.path.join(RAW, "dem_2025.tif")); Z = dem.read(1)
dsm = rasterio.open(os.path.join(RAW, "dsm_2025.tif")).read(1)
z21 = rasterio.open(os.path.join(RAW, "dem_2021.tif")).read(1)
gy, gx = np.gradient(Z, 1.0)
SLOPE = np.degrees(np.arctan(np.hypot(gx, gy)))
CANOPY = (dsm - Z) > 3.0
BLDMASK = ~geometry_mask([bld_union], out_shape=Z.shape, transform=dem.transform) if not bld_union.is_empty else np.zeros_like(Z, bool)
DZ = Z - z21

def nearest(key, items, g, maxd=150):
    if key not in T: return None, None
    idx = T[key].query(g.buffer(maxd))
    best = None
    for i in idx:
        d = items[i][0].distance(g)
        if best is None or d < best[0]: best = (d, items[i][1])
    return best if best else (None, None)

# LINZ titles (type and estate only; no owner names) and non-primary parcels (easements, land covenants)
TITLES = {p["title_no"]: p for _, p in load("titles")}
NONPRI = load("nonprimary_parcels"); T_NP = STRtree([g for g, _ in NONPRI]) if NONPRI else None

rows = []
for uid, (g, p) in enumerate(units):
    tnos = [t.strip() for t in (p.get("titles") or "").split(",") if t.strip()]
    tts = sorted({TITLES[t]["type"] for t in tnos if t in TITLES})
    np_hits = [NONPRI[i][1]["parcel_intent"] for i in (T_NP.query(g) if T_NP else [])
               if NONPRI[i][0].intersection(g).area > 1]
    extra = dict(title_types=", ".join(tts) or None, title_count=len(tnos),
                 easements_n=np_hits.count("Easement"), land_covenants_n=np_hits.count("Covenant - Land"))
    r = dict(unit_id=p.get("id") or p.get("ID") or f"U{uid}", unit_source=unit_src,
             appellation=p.get("appellation"), titles=p.get("titles"), parcel_intent=p.get("parcel_intent"),
             survey_area_m2=p.get("survey_area"), area_m2=round(g.area, 1),
             # share of the unit inside the tile: terrain and overlay values cover only that share
             in_tile_pct=round(100 * g.intersection(TILE_BOX).area / g.area, 1), **extra)
    # zones and polygon overlays: overlap percentage per class value
    for n in poly_layers:
        if n not in trees: r[n] = None; continue
        hits = {}
        for i in trees[n].query(g):
            pg, pp = L[n][i]
            a = pg.intersection(g).area
            if a > 0.5:
                label = (pp.get("PDP_ZONE") or pp.get("ZONE") or pp.get("Liquefaction") or pp.get("SEVERITY")
                         or pp.get("NAME") or pp.get("Name") or n)
                hits[label] = round(hits.get(label, 0) + 100 * a / g.area, 1)
        r[n] = json.dumps(hits) if hits else None
    for n in point_layers:
        r[n] = json.dumps([pp.get("SIGNIFICANCE") for pg, pp in (L.get(n) or []) if g.buffer(1).contains(pg)]) or None
    # terrain (LINZ LiDAR 2024-25, 2021)
    m = ~geometry_mask([g], out_shape=Z.shape, transform=dem.transform, all_touched=False)
    if m.sum() == 0: m = ~geometry_mask([g], out_shape=Z.shape, transform=dem.transform, all_touched=True)
    z = Z[m]; s = SLOPE[m]
    open_ground = m & ~BLDMASK
    r.update(ground_min_m=round(float(np.nanmin(z)), 2), ground_mean_m=round(float(np.nanmean(z)), 2),
             ground_max_m=round(float(np.nanmax(z)), 2), slope_p50_deg=round(float(np.nanpercentile(s, 50)), 1),
             slope_p90_deg=round(float(np.nanpercentile(s, 90)), 1),
             building_2021_m2=int((m & BLDMASK).sum()), open_ground_m2=int(open_ground.sum()), open_ground_slope_lt5_m2=int((open_ground & (SLOPE < 5)).sum()),
             canopy_gt3m_open_pct=round(100 * float((CANOPY & open_ground).sum()) / max(1, open_ground.sum()), 1),
             dz_2021_2025_mean_m=round(float(np.nanmean(DZ[m])), 3),
             dz_2021_2025_absmax_m=round(float(np.nanmax(np.abs(DZ[m]))), 2))
    # wastewater: nearest manhole with an invert, and nearest pipe's raw attributes
    d, np_ = nearest("ww_nodes", ww_nodes, g)
    r.update(ww_mh_dist_m=None if d is None else round(d, 1), ww_mh_id=np_ and np_["asset_id"],
             ww_mh_invert_nzvd2016=np_ and np_["invert_level_nzvd2016"],
             ww_head_ground_min_minus_invert_m=None if np_ is None else round(r["ground_min_m"] - np_["invert_level_nzvd2016"], 2))
    d, pp_ = nearest("ww_pipes", ww_pipes, g)
    r.update(ww_pipe_dist_m=None if d is None else round(d, 1), ww_pipe_id=pp_ and pp_["asset_id"],
             ww_pipe_material=pp_ and pp_.get("pipe_material"), ww_pipe_dia_mm=pp_ and pp_.get("width"),
             ww_pipe_year=pp_ and pp_.get("year_installed"), ww_pipe_condition_grade=pp_ and pp_.get("condition_grade"))
    d, sp_ = nearest("sw_nodes", sw_nodes, g)
    r.update(sw_mh_dist_m=None if d is None else round(d, 1), sw_mh_invert_nzvd2016=sp_ and sp_["invert_level_nzvd2016"])
    d, wp_ = nearest("ws_pipes", ws_pipes, g)
    r.update(ws_pipe_dist_m=None if d is None else round(d, 1), ws_pipe_dia_mm=wp_ and wp_.get("nominal_diameter"))
    # flood: highest KCDC recommended building level (NZVD2016) within 10 m
    lv = [rbl[i][1]["VALUE_NZVD2016"] for i in (T["rbl"].query(g.buffer(10)) if "rbl" in T else [])
          if rbl[i][1].get("VALUE_NZVD2016") is not None and rbl[i][0].distance(g) <= 10]
    lin = [rbl[i][1]["VALUE_NZVD2016"] for i in (T["rbl"].query(g) if "rbl" in T else [])
           if rbl[i][1].get("VALUE_NZVD2016") is not None and g.contains(rbl[i][0])]
    r.update(rbl_in_parcel_n=len(lin), rbl_in_parcel_max_nzvd2016=max(lin) if lin else None,
             rbl_in_parcel_max_minus_ground_mean_m=round(max(lin) - r["ground_mean_m"], 2) if lin else None)
    r.update(rbl_max_nzvd2016=max(lv) if lv else None,
             ground_min_minus_rbl_m=round(r["ground_min_m"] - max(lv), 2) if lv else None)
    rows.append(r)

db = duckdb.connect(os.path.join(D, "tile.duckdb"))
import pandas as pd
df = pd.DataFrame(rows)
db.execute("CREATE OR REPLACE TABLE units AS SELECT * FROM df")
prov = json.load(open(os.path.join(D, "provenance.json")))
db.execute("CREATE OR REPLACE TABLE provenance (source VARCHAR, json VARCHAR)")
db.executemany("INSERT INTO provenance VALUES (?, ?)", [(k, json.dumps(v)) for k, v in prov["sources"].items()])
print(f"compiled {len(rows)} units, {df.shape[1]} columns in {time.time()-t0:.1f}s")
