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
from overlays import class_shares, points_on, nearest_item, deepest_invert, worst_grade, largest_diameter, as_int
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
               "flood_river_corridor", "flood_stream_corridor", "flood_overflow_path", "flood_residual_overflow",
               "flood_fill_control", "flood_storage", "flood_ponding", "flood_residual_ponding", "flood_shallow_surface",
               "wind_stainless", "wind_very_high", "tsunami_zones", "earthworks", "ovl_fault_avoidance",
               "gw_liquefaction", "gw_eq_slope_failure"]
point_layers = ["ovl_heritage_places", "ovl_notable_trees"]
L = {n: load(n) for n in poly_layers + point_layers}
trees = {n: STRtree([g for g, _ in v]) for n, v in L.items() if v}

# council-owned assets in use only (status INUS = "KCDC"); excludes private, abandoned, removed and proposed assets
council = lambda items: [(g, p) for g, p in items if p.get("status") == "INUS"]
# manholes only (node types WWMH, SWMH): not cleaning eyes, valves, culvert ends, sumps or soakage (T-44)
ww_nodes = [(g, p) for g, p in council(load("ww_node")) if p.get("node_type") == "WWMH" and p.get("invert_level_nzvd2016") is not None]
sw_nodes = [(g, p) for g, p in council(load("sw_point")) if p.get("node_type") == "SWMH" and p.get("invert_level_nzvd2016") is not None]
# water mains only: reticulation, rider and trunk mains carrying treated water; not 20 mm service connections, scour
# or plant pipework, or raw untreated-water pipes (T-54)
WATER_MAINS = {"RETI", "RIDE", "TRNK"}
ww_pipes = council(load("ww_pipe"))
ws_pipes = [(g, p) for g, p in council(load("ws_pipe")) if p.get("pipe_type") in WATER_MAINS and p.get("usage") != "RAW"]
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
# district-scale flow and surroundings (district_flow.py, 10 m): whole catchments, and mean ground within ±500 m
DF_PATH = os.path.join(RAW, "district_flow.tif")
DF = None
if os.path.exists(DF_PATH):
    _src = rasterio.open(DF_PATH)
    _x0, _y0, _x1, _y1 = te.lidar_bbox(D)
    _win = from_bounds(_x0 - 20, _y0 - 20, _x1 + 20, _y1 + 20, _src.transform).round_offsets().round_lengths()
    DF = dict(acc=_src.read(1, window=_win, boundless=True, fill_value=np.nan),
              trunc=_src.read(2, window=_win, boundless=True, fill_value=np.nan),
              mean500=_src.read(3, window=_win, boundless=True, fill_value=np.nan),
              ground=_src.read(4, window=_win, boundless=True, fill_value=-9999.0),  # -9999: outside the grid
              transform=_src.window_transform(_win))
else:
    print("no district_flow.tif: catchment and wind relative height columns stay empty")


# the sea: the 1 m DEM stores it as a flat surface near -0.6 m, not as no data. Cells the district grid marks as sea
# (no value there, inside the grid) and no higher than 0.5 m are set to no data, so flow can leave into the sea (T-47).
SEA = np.zeros(Z.shape, bool); G10 = None
LIDAR_BOX = box(*rasterio.transform.array_bounds(Z.shape[0], Z.shape[1], dem.transform)) if HAVE_LIDAR else box(0, 0, 0, 0)
if DF is not None and HAVE_LIDAR:
    from rasterio.warp import reproject, Resampling
    G10 = np.full(Z.shape, -9999.0, np.float32)
    reproject(DF["ground"], G10, src_transform=DF["transform"], src_crs="EPSG:2193", dst_transform=dem.transform,
              dst_crs="EPSG:2193", src_nodata=-9999.0, dst_nodata=-9999.0, resampling=Resampling.nearest)
    with np.errstate(invalid="ignore"):
        SEA = np.isnan(G10) & ~(Z > 0.5)  # also sea the survey left as no data
    import measures as _M
    SEA = _M.extend_sea(SEA, Z)  # shoreline cells at the flat sea value the 10 m grid counts as land
    Z[SEA] = np.nan; dsm[SEA] = np.nan; z21[SEA] = np.nan
    print(f"sea cells masked: {int(SEA.sum())}")


gy, gx = np.gradient(Z, 1.0)
SLOPE = np.degrees(np.arctan(np.hypot(gx, gy)))
CANOPY = (dsm - Z) > 3.0
with np.errstate(invalid="ignore"):
    CLEAR25 = (dsm - Z) <= 0.5  # nothing standing above the ground in 2025 (T-56)
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
# the block's own LiDAR epoch offset: median 2024-25 minus 2021 on flat, open, unbuilt ground (as QA check 3)
# flat (slope under 2°) and clear (DSM within 0.5 m of the DEM, which excludes roofs and trees); the 2021 building
# outlines are not used, so the offset depends only on LiDAR (T-54)
_flat = (SLOPE < 2) & ((dsm - Z) < 0.5) & np.isfinite(DZ)
EPOCH_OFFSET = round(float(np.median(DZ[_flat])), 3) if _flat.sum() >= 1000 else None
del _flat

def district_cells(g):
    """Values of the 10 m district rasters on cells whose centre is in the parcel (or the cell holding its
    representative point, for a parcel too small to contain a centre)."""
    T_ = DF["transform"]; x0, y0, x1, y1 = g.bounds
    c0, c1 = int(math.floor((x0 - T_.c) / T_.a)), int(math.ceil((x1 - T_.c) / T_.a))
    r0, r1 = int(math.floor((y1 - T_.f) / T_.e)), int(math.ceil((y0 - T_.f) / T_.e))
    r0, c0 = max(r0, 0), max(c0, 0); r1, c1 = min(r1, DF["acc"].shape[0]), min(c1, DF["acc"].shape[1])
    if r1 <= r0 or c1 <= c0: return None
    m = ~geometry_mask([g], out_shape=(r1 - r0, c1 - c0), transform=rasterio.windows.transform(Window(c0, r0, c1 - c0, r1 - r0), T_), all_touched=False)
    if not m.any():
        p_ = g.representative_point(); c, r = int((p_.x - T_.c) / T_.a), int((p_.y - T_.f) / T_.e)
        if not (0 <= r < DF["acc"].shape[0] and 0 <= c < DF["acc"].shape[1]): return None
        return {k: DF[k][r:r + 1, c] for k in ("acc", "trunc")}
    return {k: DF[k][r0:r1, c0:c1][m] for k in ("acc", "trunc")}


def district_at(key, x, y):
    T_ = DF["transform"]; c, r = int((x - T_.c) / T_.a), int((y - T_.f) / T_.e)
    a = DF[key]
    return float(a[r, c]) if 0 <= r < a.shape[0] and 0 <= c < a.shape[1] else float("nan")


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
    CLEAR = M.ground_clear(dsm, Z)              # nothing above the ground: sun on the ground, not on a canopy
    WINTER = np.zeros(Z.shape, np.uint8)        # hours of direct sun on the ground on 21 June (hourly, NZST)
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
            if mo == 6: WINTER += (lit & CLEAR).astype(np.uint8)
            del lit, cosi
    del sb, cb
    # flow may enter the window across its edge, or from unsurveyed land next to a LiDAR gap (not from the sea)
    from scipy.ndimage import binary_dilation
    INFLOW = np.zeros(Z.shape, bool); INFLOW[0, :] = INFLOW[-1, :] = INFLOW[:, 0] = INFLOW[:, -1] = True
    GAP = ~np.isfinite(Z) & ~SEA
    OUTSIDE = np.full(Z.shape, np.nan, np.float32)  # what lies in no-data cells: the 10 m ground in a survey gap; NaN is sea
    if G10 is not None:
        land = GAP & np.isfinite(G10) & (G10 > -9000)
        OUTSIDE[land] = G10[land]
        GAP = land  # a gap over land where flow may come from; without the grid, every gap counts
    INFLOW |= binary_dilation(GAP)
    ACC, ACC_TRUNC, STEP = M.flow_routing(Z, dem.transform, inflow=INFLOW, outside=OUTSIDE)  # upslope m², flow from outside, step m
    del INFLOW, GAP, OUTSIDE
    # earthworks: 15 m × 15 m level platform, estimated from local spread of ground levels (modelled)
    zf = np.where(np.isfinite(Z), Z, 0).astype(np.float64); ok = np.isfinite(Z) & ~BLDMASK
    k = 15; n_ok = uniform_filter(ok.astype(np.float32), k, mode="constant")
    mz = uniform_filter(zf * ok, k, mode="constant"); mz2 = uniform_filter(zf * zf * ok, k, mode="constant")
    with np.errstate(invalid="ignore", divide="ignore"):
        PLAT = np.where(n_ok > 0.999, 225 * np.sqrt(np.clip(mz2 / n_ok - (mz / n_ok) ** 2, 0, None)) * math.sqrt(2 / math.pi), np.nan).astype(np.float32)
    del zf, mz, mz2, n_ok
    # wind exposure inputs: obstruction share within ±100 m, and ground relative to the surrounding ±500 m
    OBS = uniform_filter(((dsm - Z) > 2.5).astype(np.float32), 201, mode="nearest")
    print(f"measures computed in {time.time()-tm:.0f}s (lat {LAT:.3f})")

def nearest(key, items, g, maxd=150, prefer=None):
    """(distance, properties, tied ids) of the nearest asset within maxd metres; see overlays.nearest_item."""
    if key not in T: return None, None, []
    return nearest_item(items, T[key].query(g.buffer(maxd)), g, prefer=prefer, maxd=maxd)

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
    pid = p.get("id") or p.get("ID")
    if pid is None: raise SystemExit(f"parcel {uid} has no id: refusing to invent one")
    r = dict(unit_id=pid, unit_source=unit_src, block_id=te.BLOCK_ID,
             geometry_source=p.get("geometry_source") or "KCDC mirror", appellation=p.get("appellation"), titles=p.get("titles"), parcel_intent=p.get("parcel_intent"),
             survey_area_m2=p.get("survey_area"), area_m2=round(g.area, 1),
             # location for area queries (NZTM2000): a point inside the parcel, and its bounding box (T-36)
             rep_x=round(g.representative_point().x, 1), rep_y=round(g.representative_point().y, 1),
             bbox_xmin=round(g.bounds[0], 1), bbox_ymin=round(g.bounds[1], 1), bbox_xmax=round(g.bounds[2], 1), bbox_ymax=round(g.bounds[3], 1),
             # share of the parcel inside the fetch window: terrain and overlay values cover only that share
             coverage_pct=round(100 * g.intersection(TILE_BOX).area / g.area, 1) if g.area else 0.0, **extra)
    # zones and polygon overlays: overlap percentage per class value
    for n in poly_layers:
        if n not in trees: r[n] = None; continue
        hits = class_shares(n, g, [L[n][i] for i in trees[n].query(g)])
        r[n] = json.dumps(hits) if hits else None
        if n == "zones":  # above 100: the source stacks zones of different types on the parcel (T-49)
            r["zones_total_pct"] = round(sum(hits.values()), 1) if hits else None
    for n in point_layers:
        idk = "BUILDING_ID" if n == "ovl_heritage_places" else "TREE_ID"
        r[n] = json.dumps(points_on(g, [L[n][i] for i in (trees[n].query(g) if n in trees else [])], idk))
    # terrain (LINZ LiDAR 2024-25, 2021)
    rs, cs, m = window_mask(g)
    Zw, Sw, Bw, Cw, Dw = Z[rs, cs], SLOPE[rs, cs], BLDMASK[rs, cs], CANOPY[rs, cs], DZ[rs, cs]
    z = Zw[m]; s = Sw[m]
    open_ground = m & ~Bw
    r.update(lidar_cells=int(np.isfinite(z).sum()),  # coverage share: M.lidar_parcel_stats below (T-49, T-59)
             ground_min_m=stat(np.min, z), ground_mean_m=stat(np.mean, z),
             ground_max_m=stat(np.max, z), slope_p50_deg=stat(lambda a: np.percentile(a, 50), s, 1),
             slope_p90_deg=stat(lambda a: np.percentile(a, 90), s, 1),
             building_2021_m2=int((m & Bw).sum()) if HAVE_LIDAR else int(round(sum(bld_geoms[i].intersection(g).area for i in (T_BLD.query(g) if T_BLD else [])))),
             open_ground_m2=int(open_ground.sum()) if HAVE_LIDAR else None,
             dz_2021_2025_mean_m=stat(np.mean, Dw[m], 3), lidar_epoch_offset_block_m=EPOCH_OFFSET, dz_2021_2025_absmax_m=stat(lambda a: np.max(np.abs(a)), Dw[m]))
    # figures that need LiDAR on the parcel: empty, not 0, where it has none (T-59); clear-ground change (T-56)
    r.update(M.lidar_parcel_stats(z, SEA[rs, cs][m], (g.intersection(LIDAR_BOX).area / g.area) if g.area else 0.0,
                                  open_ground[m], s, Cw[m], Dw[m], CLEAR25[rs, cs][m]))
    # wastewater: nearest manhole with an invert, and nearest pipe's raw attributes
    # ties (within 5 cm): the deepest invert for manholes, the worst condition grade for pipes; all tied ids reported
    d, np_, tied = nearest("ww_nodes", ww_nodes, g, prefer=deepest_invert)
    r.update(ww_mh_tied_ids=json.dumps(tied) if len(tied) > 1 else None)
    r.update(ww_mh_dist_m=None if d is None else round(d, 1), ww_mh_id=np_ and np_["asset_id"],
             ww_mh_invert_nzvd2016=np_ and np_["invert_level_nzvd2016"],
             ww_head_ground_min_minus_invert_m=None if np_ is None or r["ground_min_m"] is None else round(r["ground_min_m"] - np_["invert_level_nzvd2016"], 2))
    d, pp_, tied = nearest("ww_pipes", ww_pipes, g, prefer=worst_grade)
    r.update(ww_pipe_tied_ids=json.dumps(tied) if len(tied) > 1 else None)
    r.update(ww_pipe_dist_m=None if d is None else round(d, 1), ww_pipe_id=pp_ and pp_["asset_id"],
             ww_pipe_material=pp_ and pp_.get("pipe_material"), ww_pipe_dia_mm=pp_ and pp_.get("width"),
             ww_pipe_year=as_int(pp_ and pp_.get("year_installed")), ww_pipe_condition_grade=as_int(pp_ and pp_.get("condition_grade")))
    d, sp_, _ = nearest("sw_nodes", sw_nodes, g, prefer=deepest_invert)
    r.update(sw_mh_dist_m=None if d is None else round(d, 1), sw_mh_invert_nzvd2016=sp_ and sp_["invert_level_nzvd2016"])
    d, wp_, tied = nearest("ws_pipes", ws_pipes, g, prefer=largest_diameter)  # a tie goes to the largest main
    r.update(ws_pipe_dist_m=None if d is None else round(d, 1), ws_pipe_dia_mm=as_int(wp_ and wp_.get("nominal_diameter")),
             ws_pipe_type=wp_ and wp_.get("pipe_type"), ws_pipe_tied_ids=json.dumps(tied) if len(tied) > 1 else None)
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
    keys = ["open_ground_clear_pct", "winter_sun_hours_open_mean", "winter_sun_open_ge3h_pct", "roof_pitch_p50_deg", "roof_flat_m2",
            "roof_north_m2", "roof_solar_rel_pct", "upslope_area_max_m2", "upslope_area_truncated", "flow_path_m", "level_open_cut_m3",
            "level_open_fill_m3", "platform_15m_earthworks_min_m3", "wind_obstruction_pct", "wind_rel_height_m",
            "horizon_mean_deg", "horizon_north_deg", "sky_view_pct"]
    if not HAVE_LIDAR or r["lidar_cells"] == 0:
        r.update({k: None for k in keys})
    else:
        og = open_ground & np.isfinite(Zw); roof = m & Bw
        ogc = og & CLEAR[rs, cs]   # open ground with nothing standing above it (no tree, shrub, fence or new roof)
        wh = WINTER[rs, cs][ogc]
        r.update(open_ground_clear_pct=round(100 * float(ogc.sum()) / og.sum(), 1) if og.any() else None,
                 winter_sun_hours_open_mean=round(float(wh.mean()), 1) if wh.size else None,
                 winter_sun_open_ge3h_pct=round(100 * float((wh >= 3).mean()), 1) if wh.size else None)
        pr, ar, ir = PITCH[rs, cs][roof], ASPECT[rs, cs][roof], IRR[rs, cs][roof]
        north = (pr >= 5) & ((ar >= 315) | (ar < 45))
        r.update(roof_pitch_p50_deg=stat(np.median, pr, 1),
                 roof_flat_m2=int((pr < 5).sum()), roof_north_m2=int(north.sum()),
                 roof_solar_rel_pct=round(100 * float(ir.mean()) / IRR_FLAT, 1) if ir.size and IRR_FLAT else None)
        a, tr_, st = ACC[rs, cs][m], ACC_TRUNC[rs, cs][m], STEP[rs, cs][m]
        fin = np.isfinite(a)
        if fin.any():
            k_ = int(np.nanargmax(np.where(fin, a, -1)))
            r.update(upslope_area_max_m2=round(float(a[k_]), 0), upslope_area_truncated=bool(tr_[k_]),
                     flow_path_m=round(float(np.nansum(st[fin & (a >= 2000)])), 1))
        else: r.update(upslope_area_max_m2=None, upslope_area_truncated=None, flow_path_m=None)
        zo = Zw[og]
        if zo.size:
            med = float(np.median(zo))
            r.update(level_open_cut_m3=round(float(np.clip(zo - med, 0, None).sum()), 0),
                     level_open_fill_m3=round(float(np.clip(med - zo, 0, None).sum()), 0))
        else: r.update(level_open_cut_m3=None, level_open_fill_m3=None)
        # platform: only where a whole 15 m × 15 m square fits on the parcel's open ground
        r.update(platform_15m_earthworks_min_m3=stat(np.min, PLAT[rs, cs][M.platform_centres(og)], 0))
        # viewpoint: the most open spot on the section, the clear open-ground cell farthest from buildings, trees and
        # the boundary (none if every open cell is under trees)
        kk = M.viewpoint(og, CLEAR[rs, cs])
        if kk is not None: pr_, pc = int(kk[0] + rs.start), int(kk[1] + cs.start)
        if kk is not None and np.isfinite(Z[pr_, pc]):
            # wind: the inputs only. A modelled exposure class disagreed with KCDC's wind zones (T-37) and is withheld.
            ob = float(OBS[pr_, pc]) * 100
            vx, vy = dem.transform * (pc + 0.5, pr_ + 0.5)
            rh = float(Z[pr_, pc]) - district_at("mean500", vx, vy) if DF is not None else float("nan")
            hz = M.horizon(dsm, Z, pr_, pc)
            r.update(wind_obstruction_pct=round(ob, 1), wind_rel_height_m=round(rh, 1) if math.isfinite(rh) else None,
                     horizon_mean_deg=round(float(np.mean(hz)), 1) if hz else None,
                     horizon_north_deg=round(max(hz[15], hz[0], hz[1]), 1) if hz else None,
                     sky_view_pct=round(100 * (1 - float(np.mean(np.sin(np.radians(hz))))), 1) if hz else None)
        else:
            r.update(wind_obstruction_pct=None, wind_rel_height_m=None,
                     horizon_mean_deg=None, horizon_north_deg=None, sky_view_pct=None)
    # whole-catchment upslope area from the district 10 m flow (available with or without LiDAR on the parcel)
    dc = district_cells(g) if DF is not None else None
    if dc is not None and np.isfinite(dc["acc"]).any():
        k_ = int(np.nanargmax(np.where(np.isfinite(dc["acc"]), dc["acc"], -1)))
        r.update(catchment_area_max_m2=round(float(dc["acc"][k_]), 0), catchment_truncated=bool(dc["trunc"][k_] > 0))
    else: r.update(catchment_area_max_m2=None, catchment_truncated=None)
    rows.append(r)

db = duckdb.connect(os.path.join(D, "tile.duckdb"))
import pandas as pd
df = pd.DataFrame(rows)
for c_ in ("ww_pipe_year", "ww_pipe_condition_grade", "ws_pipe_dia_mm", "ww_pipe_dia_mm"):  # whole numbers, kept whole
    if c_ in df: df[c_] = pd.to_numeric(df[c_], errors="coerce").round().astype("Int64")
db.execute("CREATE OR REPLACE TABLE units AS SELECT * FROM df")
db.execute(f"COPY units TO '{os.path.join(D, 'units.parquet')}' (FORMAT PARQUET)")
prov = json.load(open(os.path.join(D, "provenance.json")))
if DF is not None and os.path.exists(DF_PATH + ".json"):  # district flow raster: built once per district run
    m_ = json.load(open(DF_PATH + ".json"))
    prov["sources"]["district_flow"] = dict(ok=True, url=m_["sources"][0]["collection"], sha256=m_["sha256"], fetched=m_["fetched"],
                                            licence="LINZ CC BY 4.0 (national 1 m DEM; gaps from the contour-interpolated 8 m DEM)",
                                            res_m=m_["res_m"], bbox=m_["bbox"], inputs=m_["sources"])
    json.dump(prov, open(os.path.join(D, "provenance.json"), "w"), indent=1)
db.execute("CREATE OR REPLACE TABLE provenance (source VARCHAR, json VARCHAR)")
db.executemany("INSERT INTO provenance VALUES (?, ?)", [(k, json.dumps(v)) for k, v in prov["sources"].items()])
print(f"compiled {len(rows)} units, {df.shape[1]} columns in {time.time()-t0:.1f}s")
