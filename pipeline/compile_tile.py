"""Compile per-parcel raw primitives for one block into DuckDB and Parquet.

Unit = LINZ parcel if data/raw/parcels.geojson exists, otherwise KCDC building outline (stand-in,
labelled as such). Every column group names its source key in provenance.json. No scores,
no opinions: overlaps, distances, elevations and the raw attributes of the nearest assets.
"""
import json, os, sys, time, math, warnings
import numpy as np, duckdb, rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, Window
import tile_env as te
from shapely.geometry import shape, Point, box
from shapely.strtree import STRtree
from shapely.ops import unary_union

D = sys.argv[1] if len(sys.argv) > 1 else "data"
RAW = os.path.join(D, "raw")
t0 = time.time()
TILE_BOX = box(*te.fetch_bbox(D))  # fetch window; values cover only the part of a parcel inside it
warnings.filterwarnings("ignore", category=RuntimeWarning)  # all-NaN cells where LiDAR is missing

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

# council-owned assets in use only (status INUS = "KCDC"); excludes private, abandoned, removed and proposed assets
council = lambda items: [(g, p) for g, p in items if p.get("status") == "INUS"]
ww_nodes = [(g, p) for g, p in council(load("ww_node")) if p.get("invert_level_nzvd2016") is not None]
sw_nodes = [(g, p) for g, p in council(load("sw_point")) if p.get("invert_level_nzvd2016") is not None]
ww_pipes = council(load("ww_pipe")); ws_pipes = council(load("ws_pipe"))
rbl = load("flood_rbl_nzvd2016")
T = {k: STRtree([g for g, _ in v]) for k, v in dict(ww_nodes=ww_nodes, sw_nodes=sw_nodes, ww_pipes=ww_pipes,
                                                    ws_pipes=ws_pipes, rbl=rbl).items() if v}
bld_geoms = [g for g, _ in load("buildings_2021")]

HAVE_LIDAR = all(os.path.exists(os.path.join(RAW, n + ".tif")) for n in ("dem_2025", "dsm_2025", "dem_2021"))
if not HAVE_LIDAR:  # outside the LiDAR surveys (for example the Tararua foothills): terrain columns stay empty
    print("no LiDAR for this window")
    class _NoDem: transform = rasterio.transform.from_origin(0, 0, 1, 1)
    dem = _NoDem(); Z = dsm = z21 = np.full((3, 3), np.nan, dtype="float32")
else:
    dem = rasterio.open(os.path.join(RAW, "dem_2025.tif")); Z = dem.read(1)
    dsm = rasterio.open(os.path.join(RAW, "dsm_2025.tif")).read(1)
    z21 = rasterio.open(os.path.join(RAW, "dem_2021.tif")).read(1)
gy, gx = np.gradient(Z, 1.0)
SLOPE = np.degrees(np.arctan(np.hypot(gx, gy)))
CANOPY = (dsm - Z) > 3.0
BLDMASK = ~geometry_mask(bld_geoms, out_shape=Z.shape, transform=dem.transform) if bld_geoms and HAVE_LIDAR else np.zeros_like(Z, bool)
T_BLD = STRtree(bld_geoms) if bld_geoms else None

def window_mask(g):
    """Cells of the parcel, computed in a small window around it: (row slice, col slice, mask)."""
    if not HAVE_LIDAR: return slice(0, 0), slice(0, 0), np.zeros((0, 0), bool)
    T_ = dem.transform; x0, y0, x1, y1 = g.bounds
    c0, c1 = int(math.floor((x0 - T_.c) / T_.a)) - 1, int(math.ceil((x1 - T_.c) / T_.a)) + 1
    r0, r1 = int(math.floor((y1 - T_.f) / T_.e)) - 1, int(math.ceil((y0 - T_.f) / T_.e)) + 1
    r0, c0, r1, c1 = max(0, r0), max(0, c0), min(Z.shape[0], r1), min(Z.shape[1], c1)
    if r1 <= r0 or c1 <= c0: return slice(0, 0), slice(0, 0), np.zeros((0, 0), bool)
    tr = rasterio.windows.transform(Window(c0, r0, c1 - c0, r1 - r0), dem.transform)
    sh = (r1 - r0, c1 - c0)
    m = ~geometry_mask([g], out_shape=sh, transform=tr, all_touched=False)
    if m.sum() == 0: m = ~geometry_mask([g], out_shape=sh, transform=tr, all_touched=True)
    return slice(r0, r1), slice(c0, c1), m

def stat(f, a, nd=2):
    a = a[np.isfinite(a)]
    return None if a.size == 0 else round(float(f(a)), nd)
DZ = Z - z21

# ---- computed measures (T-37): sun, shading, roofs, overland flow, earthworks, wind exposure, horizon ----
import measures as M
from scipy.ndimage import uniform_filter
from pyproj import Transformer
tm = time.time()
if HAVE_LIDAR:
    H_, W_ = Z.shape
    cx, cy = dem.transform * (W_ / 2, H_ / 2)
    LON, LAT = Transformer.from_crs(2193, 4326, always_xy=True).transform(cx, cy)
    # roof and ground surface orientation from the DSM
    dgy, dgx = np.gradient(dsm, 1.0)
    PITCH = np.degrees(np.arctan(np.hypot(dgx, dgy))).astype(np.float32)
    ASPECT = (np.degrees(np.arctan2(-dgx, dgy)) % 360).astype(np.float32)   # direction the surface faces, from north
    del dgx, dgy
    sb, cb = np.sin(np.radians(PITCH)), np.cos(np.radians(PITCH))
    WINTER = np.zeros(Z.shape, np.uint8)        # hours of direct sun on 21 June (hourly, NZST)
    IRR = np.zeros(Z.shape, np.float32)          # clear-sky direct irradiation on the surface, 3 representative days
    IRR_FLAT = 0.0                               # the same for an unshaded horizontal surface
    for (mo, dd) in ((6, 21), (3, 20), (12, 21)):
        for hr, az, alt in M.day_positions(LAT, LON, mo, dd):
            lit = M.sunlit(dsm, az, alt)
            am = 1 / max(math.sin(math.radians(alt)), 0.05)
            dni = 1353 * 0.7 ** (am ** 0.678)  # Meinel clear-sky beam
            cosi = np.clip(math.sin(math.radians(alt)) * cb + math.cos(math.radians(alt)) * sb *
                           np.cos(np.radians(az - ASPECT)), 0, None)
            IRR += (dni * cosi * lit).astype(np.float32)
            IRR_FLAT += dni * math.sin(math.radians(alt))
            if mo == 6: WINTER += lit.astype(np.uint8)
            del lit, cosi
    del sb, cb
    ACC = M.flow_accumulation(Z, dem.transform)                   # upslope area, m²
    # earthworks: 15 m × 15 m level platform, estimated from local spread of ground levels (modelled)
    zf = np.where(np.isfinite(Z), Z, 0).astype(np.float64); ok = np.isfinite(Z) & ~BLDMASK
    k = 15; n_ok = uniform_filter(ok.astype(np.float32), k, mode="constant")
    mz = uniform_filter(zf * ok, k, mode="constant"); mz2 = uniform_filter(zf * zf * ok, k, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        PLAT = np.where(n_ok > 0.999, 225 * np.sqrt(np.clip(mz2 / n_ok - (mz / n_ok) ** 2, 0, None)) * math.sqrt(2 / math.pi), np.nan).astype(np.float32)
    del zf, mz, mz2, n_ok
    # wind exposure inputs: obstruction share within ±100 m, and ground relative to the surrounding ±500 m
    OBS = uniform_filter(((dsm - Z) > 2.5).astype(np.float32), 201, mode="nearest")
    zf = np.where(np.isfinite(Z), Z, np.nanmean(Z)).astype(np.float32)
    RELH = (zf - uniform_filter(zf, 1001, mode="nearest")).astype(np.float32); del zf
    print(f"measures computed in {time.time()-tm:.0f}s (lat {LAT:.3f})")

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
    r = dict(unit_id=p.get("id") or p.get("ID") or f"U{uid}", unit_source=unit_src, block_id=te.BLOCK_ID,
             appellation=p.get("appellation"), titles=p.get("titles"), parcel_intent=p.get("parcel_intent"),
             survey_area_m2=p.get("survey_area"), area_m2=round(g.area, 1),
             # share of the parcel inside the fetch window: terrain and overlay values cover only that share
             coverage_pct=round(100 * g.intersection(TILE_BOX).area / g.area, 1) if g.area else 0.0, **extra)
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
        gb = g.buffer(1)
        r[n] = json.dumps([L[n][i][1].get("SIGNIFICANCE") for i in (trees[n].query(gb) if n in trees else [])
                           if gb.contains(L[n][i][0])])
    # terrain (LINZ LiDAR 2024-25, 2021)
    rs, cs, m = window_mask(g)
    Zw, Sw, Bw, Cw, Dw = Z[rs, cs], SLOPE[rs, cs], BLDMASK[rs, cs], CANOPY[rs, cs], DZ[rs, cs]
    z = Zw[m]; s = Sw[m]
    open_ground = m & ~Bw
    r.update(lidar_cells=int(np.isfinite(z).sum()), ground_min_m=stat(np.min, z), ground_mean_m=stat(np.mean, z),
             ground_max_m=stat(np.max, z), slope_p50_deg=stat(lambda a: np.percentile(a, 50), s, 1),
             slope_p90_deg=stat(lambda a: np.percentile(a, 90), s, 1),
             building_2021_m2=int((m & Bw).sum()) if HAVE_LIDAR else int(round(sum(bld_geoms[i].intersection(g).area for i in (T_BLD.query(g) if T_BLD else [])))),
             open_ground_m2=int(open_ground.sum()) if HAVE_LIDAR else None,
             open_ground_slope_lt5_m2=int((open_ground & (Sw < 5)).sum()) if HAVE_LIDAR else None,
             canopy_gt3m_open_pct=round(100 * float((Cw & open_ground).sum()) / max(1, open_ground.sum()), 1) if HAVE_LIDAR else None,
             dz_2021_2025_mean_m=stat(np.mean, Dw[m], 3), dz_2021_2025_absmax_m=stat(lambda a: np.max(np.abs(a)), Dw[m]))
    # wastewater: nearest manhole with an invert, and nearest pipe's raw attributes
    d, np_ = nearest("ww_nodes", ww_nodes, g)
    r.update(ww_mh_dist_m=None if d is None else round(d, 1), ww_mh_id=np_ and np_["asset_id"],
             ww_mh_invert_nzvd2016=np_ and np_["invert_level_nzvd2016"],
             ww_head_ground_min_minus_invert_m=None if np_ is None or r["ground_min_m"] is None else round(r["ground_min_m"] - np_["invert_level_nzvd2016"], 2))
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
             rbl_in_parcel_max_minus_ground_mean_m=round(max(lin) - r["ground_mean_m"], 2) if lin and r["ground_mean_m"] is not None else None)
    r.update(rbl_max_nzvd2016=max(lv) if lv else None,
             ground_min_minus_rbl_m=round(r["ground_min_m"] - max(lv), 2) if lv and r["ground_min_m"] is not None else None)
    # computed measures (T-37); modelled or derived, see SOURCES.md
    keys = ["winter_sun_hours_open_mean", "winter_sun_open_ge3h_pct", "roof_pitch_p50_deg", "roof_flat_m2",
            "roof_north_m2", "roof_solar_rel_pct", "upslope_area_max_m2", "flow_path_m", "level_open_cut_m3",
            "level_open_fill_m3", "platform_15m_earthworks_min_m3", "wind_obstruction_pct", "wind_rel_height_m",
            "wind_exposure_class", "horizon_mean_deg", "horizon_north_deg", "sky_view_pct"]
    if not HAVE_LIDAR or r["lidar_cells"] == 0:
        r.update({k: None for k in keys})
    else:
        og = open_ground & np.isfinite(Zw); roof = m & Bw
        wh = WINTER[rs, cs][og]
        r.update(winter_sun_hours_open_mean=round(float(wh.mean()), 1) if wh.size else None,
                 winter_sun_open_ge3h_pct=round(100 * float((wh >= 3).mean()), 1) if wh.size else None)
        pr, ar, ir = PITCH[rs, cs][roof], ASPECT[rs, cs][roof], IRR[rs, cs][roof]
        north = (pr >= 5) & ((ar >= 315) | (ar < 45))
        r.update(roof_pitch_p50_deg=stat(np.median, pr, 1),
                 roof_flat_m2=int((pr < 5).sum()), roof_north_m2=int(north.sum()),
                 roof_solar_rel_pct=round(100 * float(ir.mean()) / IRR_FLAT, 1) if ir.size and IRR_FLAT else None)
        a = ACC[rs, cs][m]
        r.update(upslope_area_max_m2=stat(np.max, a, 0), flow_path_m=int((a >= 2000).sum()))
        zo = Zw[og]
        if zo.size:
            med = float(np.median(zo))
            r.update(level_open_cut_m3=round(float(np.clip(zo - med, 0, None).sum()), 0),
                     level_open_fill_m3=round(float(np.clip(med - zo, 0, None).sum()), 0))
        else: r.update(level_open_cut_m3=None, level_open_fill_m3=None)
        r.update(platform_15m_earthworks_min_m3=stat(np.min, PLAT[rs, cs][m], 0))
        # viewpoint: the most open spot on the section, the open-ground cell farthest from buildings and the boundary
        from scipy.ndimage import distance_transform_edt
        if og.any():
            dist = distance_transform_edt(og)
            kk = np.unravel_index(int(np.argmax(dist)), dist.shape)
            pr_, pc = int(kk[0] + rs.start), int(kk[1] + cs.start)
        if og.any() and np.isfinite(Z[pr_, pc]):
            ob, rh = float(OBS[pr_, pc]) * 100, float(RELH[pr_, pc])
            cls = "exposed" if (ob < 10 or rh > 15) else "sheltered" if (ob >= 40 and rh < 5) else "partly sheltered"
            hz = M.horizon(dsm, Z, pr_, pc)
            r.update(wind_obstruction_pct=round(ob, 1), wind_rel_height_m=round(rh, 1), wind_exposure_class=cls,
                     horizon_mean_deg=round(float(np.mean(hz)), 1) if hz else None,
                     horizon_north_deg=round(max(hz[15], hz[0], hz[1]), 1) if hz else None,
                     sky_view_pct=round(100 * (1 - float(np.mean(np.sin(np.radians(hz))))), 1) if hz else None)
        else:
            r.update(wind_obstruction_pct=None, wind_rel_height_m=None, wind_exposure_class=None,
                     horizon_mean_deg=None, horizon_north_deg=None, sky_view_pct=None)
    rows.append(r)

db = duckdb.connect(os.path.join(D, "tile.duckdb"))
import pandas as pd
df = pd.DataFrame(rows)
db.execute("CREATE OR REPLACE TABLE units AS SELECT * FROM df")
db.execute(f"COPY units TO '{os.path.join(D, 'units.parquet')}' (FORMAT PARQUET)")
prov = json.load(open(os.path.join(D, "provenance.json")))
db.execute("CREATE OR REPLACE TABLE provenance (source VARCHAR, json VARCHAR)")
db.executemany("INSERT INTO provenance VALUES (?, ?)", [(k, json.dumps(v)) for k, v in prov["sources"].items()])
print(f"compiled {len(rows)} units, {df.shape[1]} columns in {time.time()-t0:.1f}s")
