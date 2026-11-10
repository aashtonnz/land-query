"""Build the public map site (T-105, D-23, D-24) into a folder for GitHub Pages.

Usage: python3 site/build_map.py OUT_DIR. Reads the published results (`kapiti-results`, `porirua-results`, public-mode
columns only, D-12) and the national index pilot (`national-pilot`), and writes:

- index.html and map.js: the page (site/map.html, site/map.js);
- data/meta.json: council figures, the level and piece index, the coastline and the field lists;
- data/v/{measure}.bin: one measure for every parcel (float32, NaN for none), in the order of meta.json's parcels,
  fetched only when chosen;
- data/L{level}/{key}.bin: parcel shapes, each with its place in the value files, cut into squares at four levels of detail
  (LEVELS), so the page downloads only the pieces in view. At the simpler levels a parcel too small to keep its
  shape becomes a square of its own area at its point, so every parcel always covers its share of the land;
- data/detail/{key}.json: each parcel's values for the side panel, in the finest level's squares;
- data/search.json: legal descriptions and addresses for search.

Piece format (little-endian): "LQC1", parcels n, rings nr, vertices nv (uint32); ids (int32 × n); each parcel's place in the
value files (float32 × n; -1 for water); ring vertex counts (uint32 × nr, top bit set for a hole, which follows its outer
ring); each ring's first vertex (int32 x, y in half-metres); rings per parcel (uint16 × n, padded to 4 bytes);
council (uint8 × n, padded to 4 bytes); then each later vertex as a step from the one before (int16 x, y, half-metres;
a longer step is split).
"""
import json, math, os, shutil, struct, subprocess, sys, tempfile
import duckdb, numpy as np
from shapely import wkb
from shapely.geometry import box, shape
from shapely import clip_by_rect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
OUT = sys.argv[1] if len(sys.argv) > 1 else "map-site"
ORIGIN = (1600000, 5300000)          # piece squares are counted from here (NZTM2000)
# (square side m, simplification m): full detail for street level, then simpler shapes for zoomed-out views. Each
# level is used once a tile pixel covers at least twice its simplification (map.js levelFor), so simplifying never
# shows; only parcels smaller than the simplification become squares of their own area
LEVELS = [(2048, 0.5), (16384, 2.0), (65536, 8.0), (262144, 24.0)]
# every value the map can be coloured by: (column, label, unit, group, scale). Scale: "lin", "sqrt" or "log", over the
# 2nd to 98th percentile unless FIXED says otherwise. A parcel without the value is drawn grey. Each measure is written
# once, as data/v/{column}.bin (float32 per parcel, in the order of the sorted parcel ids; each shape carries its place), and downloaded only when chosen
MEASURES = [
    ("area_m2", "Parcel area", "m²", "Size and shape", "log"),
    ("survey_area_m2", "Surveyed area (on the survey plan)", "m²", "Size and shape", "log"),
    ("perimeter_m", "Perimeter", "m", "Size and shape", "log"),
    ("width_m", "Width (short side of the smallest rectangle around it)", "m", "Size and shape", "log"),
    ("compactness", "Compactness (1 is a circle)", "", "Size and shape", "lin"),
    ("title_count", "Titles", "", "Titles and addresses", "lin"),
    ("address_count", "Addresses", "", "Titles and addresses", "lin"),
    ("easements_n", "Easement parcels (Kāpiti and Porirua)", "", "Titles and addresses", "lin"),
    ("land_covenants_n", "Land covenants (Kāpiti and Porirua)", "", "Titles and addresses", "lin"),
    ("building_cover_pct", "Building cover (under LINZ building outlines)", "%", "Buildings", "sqrt"),
    ("building_count", "Buildings", "", "Buildings", "sqrt"),
    ("building_m2", "Building footprint", "m²", "Buildings", "log"),
    ("largest_building_m2", "Largest building", "m²", "Buildings", "log"),
    ("road_frontage_m", "Road frontage", "m", "Roads, coast and water", "sqrt"),
    ("road_frontage_via_strip_m", "Road frontage across a strip under 1 m wide", "m", "Roads, coast and water", "sqrt"),
    ("coast_distance_m", "Distance to the coast (none beyond 10 km)", "m", "Roads, coast and water", "sqrt"),
    ("water_pct", "Under water (sea, lakes, rivers)", "%", "Roads, coast and water", "lin"),
    ("ground_mean_m", "Mean ground height", "m", "Ground", "sqrt"),
    ("ground_min_m", "Lowest ground", "m", "Ground", "sqrt"),
    ("ground_max_m", "Highest ground", "m", "Ground", "sqrt"),
    ("slope_mean_deg", "Mean slope (10 m grid; national index)", "°", "Ground", "lin"),
    ("slope_max_deg", "Steepest slope (10 m grid; national index)", "°", "Ground", "lin"),
    ("slope_p50_deg", "Median slope (1 m LiDAR; Kāpiti and Porirua)", "°", "Ground", "lin"),
    ("slope_p90_deg", "Steepness, 90th percentile slope (1 m LiDAR; Kāpiti and Porirua)", "°", "Ground", "lin"),
    ("flat_pct", "Flat ground (under 5°; national index)", "%", "Ground", "lin"),
    ("steep_pct", "Steep ground (over 15°; national index)", "%", "Ground", "lin"),
    ("low_lying_pct", "Low-lying ground (under 5 m; national index)", "%", "Ground", "lin"),
    ("lidar_coverage_pct", "LiDAR coverage", "%", "Ground", "lin"),
    ("dz_2021_2025_mean_m", "Ground change 2021 to 2025, mean (Kāpiti)", "m", "Ground", "lin"),
    ("dz_2021_2025_absmax_m", "Ground change 2021 to 2025, largest (Kāpiti)", "m", "Ground", "sqrt"),
    ("dz_2021_2025_clear_pct", "Ground change 2021 to 2025, share clear of buildings and trees (Kāpiti)", "%", "Ground", "lin"),
    ("dz_2021_2025_clear_mean_m", "Ground change 2021 to 2025, mean where clear (Kāpiti)", "m", "Ground", "lin"),
    ("catchment_area_max_m2", "Upslope catchment", "m²", "Drainage", "log"),
    ("flow_path_m", "Overland flow paths (Kāpiti and Porirua)", "m", "Drainage", "sqrt"),
    ("ww_mh_dist_m", "Nearest sewer manhole (Kāpiti)", "m", "Services (Kāpiti)", "sqrt"),
    ("ww_mh_invert_nzvd2016", "Nearest sewer manhole, invert height (Kāpiti)", "m", "Services (Kāpiti)", "lin"),
    ("ww_head_ground_min_minus_invert_m", "Fall from lowest ground to the sewer invert (Kāpiti)", "m", "Services (Kāpiti)", "lin"),
    ("ww_pipe_dist_m", "Nearest sewer pipe (Kāpiti)", "m", "Services (Kāpiti)", "sqrt"),
    ("ww_pipe_dia_mm", "Nearest sewer pipe, diameter (Kāpiti)", "mm", "Services (Kāpiti)", "lin"),
    ("ww_pipe_year", "Nearest sewer pipe, year installed (Kāpiti; many recorded as 1979 or 1980, likely placeholders)", "", "Services (Kāpiti)", "lin"),
    ("ww_pipe_condition_grade", "Nearest sewer pipe, condition grade (1 very good to 5 very poor; Kāpiti)", "", "Services (Kāpiti)", "lin"),
    ("ws_pipe_dist_m", "Nearest water main (Kāpiti)", "m", "Services (Kāpiti)", "sqrt"),
    ("ws_pipe_dia_mm", "Nearest water main, diameter (Kāpiti)", "mm", "Services (Kāpiti)", "lin"),
]
FIXED = {"ground_mean_m": (0, 200), "slope_p90_deg": (0, 35), "ww_pipe_year": (1950, 2020), "ww_pipe_condition_grade": (1, 5),
         "water_pct": (0, 100), "lidar_coverage_pct": (0, 100), "flat_pct": (0, 100), "steep_pct": (0, 100), "low_lying_pct": (0, 100)}
MKEYS = [m[0] for m in MEASURES]
NATIONAL_AS = {"upslope_area_max_m2": "catchment_area_max_m2", "lidar_pct": "lidar_coverage_pct"}   # national name -> map name
COUNCILS = {"k": 0, "p": 1, "n": 2}
WATER_PCT = {}   # parcel id -> national index water_pct
WATER = 3   # council code for water (river and stream beds, lakes): drawn in the sea colour, never selected (id -1)
COUNCIL_COLS = ["unit_id", "appellation", "parcel_intent", "rep_x", "rep_y"]
KAPITI_ONLY = []
DETAIL = ["c", "appellation", "parcel_intent", "address", "territorial_authority"] + MKEYS


def results(branch):
    d = tempfile.mkdtemp()
    subprocess.run(["git", "fetch", "-q", "origin", branch], cwd=ROOT, check=True)
    tar = subprocess.run(["git", "archive", f"origin/{branch}", "results"], cwd=ROOT, check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", d], input=tar, check=True)
    return os.path.join(d, "results")


def public_columns(council, d):
    code = f"import sys; sys.path.insert(0, 'service'); from landquery import LandQuery; print(' '.join(LandQuery({d!r}, 'public').columns))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=dict(os.environ, COUNCIL=council), check=True,
                         capture_output=True, text=True).stdout
    return set(out.split())


def clean(v):
    if v is None or (isinstance(v, float) and not math.isfinite(v)): return None
    if isinstance(v, float): return round(v, 1) if abs(v) < 1e5 else round(v)
    return v


def parcels():
    """{id: dict of values} for every parcel: the councils' results where they exist, else the national index."""
    P, stats = {}, {}
    nd = results("national-pilot"); nf = os.path.join(nd, "index.parquet")
    con = duckdb.connect(); rel = con.sql(f"SELECT * FROM '{nf}'"); cols = rel.columns
    want = set(MKEYS) | set(NATIONAL_AS) | {"parcel_id", "appellation", "parcel_intent", "rep_x", "rep_y", "address", "territorial_authority", "water_pct"}
    keep = [c for c in cols if c in want]
    for r in con.sql(f"SELECT {', '.join(keep)} FROM '{nf}'").fetchall():
        row = dict(zip(keep, r)); pid = row.pop("parcel_id")
        WATER_PCT[pid] = row.get("water_pct")   # measured water share (None: unknown); parcels above 0 get their sea part drawn (T-117)
        for a, b in NATIONAL_AS.items():
            if a in row: row[b] = row.pop(a)
        row["c"] = "n"; P[pid] = row
    n_all, nmed = duckdb.sql(f"SELECT count(*), round(median(ground_mean_m), 1) FROM '{nf}'").fetchall()[0]
    stats["n"] = dict(parcels=n_all, median_ground=nmed, run="national index pilot, built from " +
                      open(os.path.join(nd, "BUILT_FROM.txt")).read().strip())
    for c, council, branch, extra in [("k", "kapiti", "kapiti-results", KAPITI_ONLY), ("p", "porirua", "porirua-results", [])]:
        d = results(branch); pub = public_columns(council, d)
        cols = ["unit_id"] + [x for x in dict.fromkeys(COUNCIL_COLS + MKEYS) if x in pub and x != "unit_id"]
        f = os.path.join(d, "units.parquet")
        for r in duckdb.sql(f"SELECT {', '.join(cols)} FROM '{f}'").fetchall():
            row = dict(zip(cols, r)); old = P.get(row["unit_id"], {})
            row.update(c=c, address=old.get("address"), territorial_authority=old.get("territorial_authority"))
            # measures the council build does not hold (or does not publish) come from the national index, same LINZ parcel
            for k in MKEYS + ["rep_x", "rep_y"]:
                if row.get(k) is None and old.get(k) is not None: row[k] = old[k]
            P[row.pop("unit_id")] = row
        n, lid, med = duckdb.sql(f"SELECT count(*), count(ground_mean_m), round(median(ground_mean_m), 1) FROM '{f}'").fetchall()[0]
        stats[c] = dict(parcels=n, with_lidar=lid, median_ground=med, run=open(os.path.join(d, "RUN.txt")).read().strip())
    shapes = {pid: b for pid, b in duckdb.sql(f"SELECT parcel_id, geometry_wkb FROM '{nf}'").fetchall()}
    # council parcels the national index does not hold (outside its region, or superseded since the council build):
    # their current shape from LINZ by id; a parcel LINZ no longer has is left off the map, never drawn as a stand-in
    # square over the parcels that replaced it (T-109)
    import arcgis
    from shapely import wkb as _wkb
    from shapely.geometry import shape as _shape
    need = [pid for pid in P if pid not in shapes]
    for i in range(0, len(need), 200):
        ids = ",".join(str(x) for x in need[i:i + 200])
        for f in arcgis.query_all("https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/LINZ_NZ_Primary_Parcels/FeatureServer/0",
                                  dict(where=f"id IN ({ids})", outFields="id", outSR=2193)):
            if f.get("geometry"): shapes[f["properties"]["id"]] = _wkb.dumps(_shape(f["geometry"]))
    gone = [pid for pid in need if pid not in shapes]
    for pid in gone: P.pop(pid)
    print(len(need), "council parcels without a national-index shape;", len(need) - len(gone), "found in LINZ,", len(gone), "superseded and left out")
    stats["superseded_left_out"] = len(gone)
    return P, shapes, stats


def square(x, y, area):
    h = max(math.sqrt(max(area or 0, 1)) / 2, 0.5)
    return box(x - h, y - h, x + h, y + h)


def level_shape(g, p, tol):
    """The parcel at this level: simplified, or a square of its own area if too small to keep its shape."""
    if g is None or g.is_empty or math.sqrt(max(p.get("area_m2") or 0, 0)) < tol:
        return square(p["rep_x"], p["rep_y"], p.get("area_m2"))
    # simplifying a section not much wider than the tolerance can collapse it; then less is simplified, so every
    # parcel keeps its area (within 10%) at every level
    for t in (tol, tol / 4, tol / 16):
        sg = g.simplify(t, preserve_topology=True)
        if not sg.is_empty and abs(sg.area - g.area) <= 0.1 * g.area: return sg
    return g


def colour_files(P, order):
    """Write data/v/{measure}.bin (float32 per parcel in `order`, NaN for none) for each measure with values, and return
    the list the page builds its menu and scales from."""
    os.makedirs(os.path.join(OUT, "data", "v"), exist_ok=True); out = []
    for key, label, unit, group, scale in MEASURES:
        a = np.array([np.nan if P[pid].get(key) is None else float(P[pid][key]) for pid in order], "<f4")
        ok = a[np.isfinite(a)]
        if len(ok) == 0 or ok.min() == ok.max(): continue   # nothing to show
        a.tofile(os.path.join(OUT, "data", "v", key + ".bin"))
        lo, hi = FIXED.get(key, (float(np.percentile(ok, 2)), float(np.percentile(ok, 98))))
        if hi <= lo: lo, hi = float(ok.min()), float(ok.max())
        if scale == "log": lo, hi = max(lo, 1.0), max(hi, 10.0)
        if scale == "sqrt": lo = max(lo, 0.0)
        out.append(dict(key=key, label=label, unit=unit, group=group, scale=scale, lo=lo, hi=hi, n=int(len(ok)),
                        clipped_lo=bool(ok.min() < lo), clipped_hi=bool(ok.max() > hi)))
    print(len(out), "measures to colour by")
    return out


def encode(items):
    """One piece: [(id, council code, [measure values], geometry)] as bytes (see the module docstring)."""
    ids, cc, vals, rper, rlen, starts, steps = [], [], [], [], [], [], []
    for pid, c, v, g in items:
        rings = [(r, k > 0) for poly in getattr(g, "geoms", [g]) if poly.geom_type == "Polygon"
                 for k, r in enumerate([poly.exterior, *poly.interiors])]
        ids.append(pid); cc.append(c); vals.append(v); rper.append(len(rings))
        for r, hole in rings:
            pts = np.round(np.asarray(r.coords)[:-1] * 2).astype(np.int64)
            if len(pts) < 3: pts = np.vstack([pts, pts[-1:] + 1, pts[-1:] + [0, 1]])[:3]
            out = [pts[0]]
            for q in pts[1:]:
                d = q - out[-1]; k = max(1, int(np.ceil(np.abs(d).max() / 32000))); base = out[-1]
                for j in range(1, k + 1): out.append(base + np.round(d * j / k).astype(np.int64))
            out = np.array(out)
            rlen.append(len(out) | (0x80000000 if hole else 0)); starts.append(out[0]); steps.append(np.diff(out, axis=0))
    nv = int(sum(n & 0x7FFFFFFF for n in rlen))
    st = np.concatenate([s for s in steps if len(s)]) if any(len(s) for s in steps) else np.zeros((0, 2))
    pad = lambda b: b + b"\0" * (-len(b) % 4)
    return (b"LQC1" + struct.pack("<3I", len(ids), len(rlen), nv) + np.array(ids, "<i4").tobytes()
            + np.array(vals, "<f4").reshape(-1).tobytes() + np.array(rlen, "<u4").tobytes()
            + np.array(starts, "<i4").reshape(-1).tobytes() + pad(np.array(rper, "<u2").tobytes())
            + pad(np.array(cc, "u1").tobytes()) + st.astype("<i2").tobytes())


def sea_parts(P, geoms, water_pct, land):
    """Each parcel's part outside the land outline, for parcels the national index measured as part water (unknown
    water, None, draws nothing). The outline is clipped to each parcel first (T-117, T-119)."""
    from shapely import STRtree, clip_by_rect
    from shapely.ops import unary_union
    lt = STRtree(land) if land else None; out = []
    for pid in P:
        g = geoms.get(pid)
        if g is None or not water_pct.get(pid) or lt is None: continue
        near = [c for c in (clip_by_rect(land[i], *g.bounds) for i in lt.query(g)) if not c.is_empty]
        sea = g.difference(unary_union(near)) if near else g
        if not sea.is_empty and sea.area > 1: out.append(sea)
    return out


def land_outline(bounds):
    """LINZ's NZ Coastline land polygons at 5 m over bounds, clipped (the national index's sea is outside these)."""
    import arcgis, overlays
    x0, y0, x1, y1 = bounds; out = []
    for f in arcgis.query_all("https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/LINZ_NZ_Coastline/FeatureServer/0",
                              dict(where="1=1", geometry=f"{x0},{y0},{x1},{y1}", geometryType="esriGeometryEnvelope", inSR=2193,
                                   spatialRel="esriSpatialRelIntersects", outFields="id", outSR=2193, maxAllowableOffset=5)):
        g = clip_by_rect(overlays.repaired(shape(f["geometry"])), x0, y0, x1, y1)
        if not g.is_empty: out.append(g)
    return out


def coastline(bounds):
    import arcgis, overlays
    x0, y0, x1, y1 = bounds; land = []
    for f in arcgis.query_all("https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/LINZ_NZ_Coastline/FeatureServer/0",
                              dict(where="1=1", geometry=f"{x0},{y0},{x1},{y1}", geometryType="esriGeometryEnvelope", inSR=2193,
                                   spatialRel="esriSpatialRelIntersects", outFields="id", outSR=2193, maxAllowableOffset=15)):
        g = clip_by_rect(overlays.repaired(shape(f["geometry"])), x0, y0, x1, y1)
        for poly in getattr(g, "geoms", [g]):
            if poly.geom_type != "Polygon" or poly.area < 2000: continue
            land.append([[int(round(v)) for xy in r.coords[:-1] for v in xy] for r in [poly.exterior, *poly.interiors]])
    return land


def water(bounds):
    """Rivers and lakes: LINZ river and stream bed parcels (not in the parcel rows) and Topo50 lake polygons, clipped."""
    import arcgis, overlays
    x0, y0, x1, y1 = bounds; out = []
    svc = "https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/"
    for url, where in [(svc + "LINZ_NZ_Primary_Parcels/FeatureServer/0", "parcel_intent IN ('Hydro','Riverbed','Streambed')"),
                       (svc + "NZ_Lake_Polygons_Topo_1_50k/FeatureServer/0", "1=1"),
                       (svc + "LINZ_NZ_River_Name_Polygons_Pilot/FeatureServer/0", "1=1")]:
        for f in arcgis.query_all(url, dict(where=where, geometry=f"{x0},{y0},{x1},{y1}", geometryType="esriGeometryEnvelope", inSR=2193,
                                            spatialRel="esriSpatialRelIntersects", outFields="OBJECTID", outSR=2193, maxAllowableOffset=0.5), workers=8):
            if not f.get("geometry"): continue
            g = clip_by_rect(overlays.repaired(shape(f["geometry"])), x0, y0, x1, y1)
            if not g.is_empty and g.area > 0: out.append((g, "Primary_Parcels" not in url))
    return out


def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "data", "detail"))
    P, shapes, stats = parcels()
    print(len(P), "parcels,", len(shapes), "shapes")
    geoms = {pid: wkb.loads(b) for pid, b in shapes.items()}
    xs = [p["rep_x"] for p in P.values()]; ys = [p["rep_y"] for p in P.values()]
    bounds = (min(xs) - 20000, min(ys) - 20000, max(xs) + 20000, max(ys) + 20000)
    order = sorted(P); idx = {pid: i for i, pid in enumerate(order)}
    meta = dict(origin=ORIGIN, levels=[], measures=["index"], colours=colour_files(P, order), councils=list(COUNCILS),
                detail_fields=DETAIL, stats=stats,
                bounds=bounds, parcels=len(P), land=coastline(bounds))
    # Topo50 lakes and LINZ's river areas (1:50k) are drawn whole, over the parcels. Three rules that cut them where
    # they overlap land parcels each erased real water (small lakes in farm parcels, rivers whose banks are parcel
    # boundaries), so none is used: an edge can stray a few metres over a section, and the legend says edges are
    # approximate. Each parcel's own water share is measured separately (national index water_pct) (T-109 to T-116)
    waters = [g for g, _ in water(bounds) if not g.is_empty and g.area > 1]
    print(len(waters), "water polygons, drawn whole")
    # the sea inside parcels (seabed and marina parcels, tidal flats) is drawn as water too: each parcel's part outside
    # LINZ's land outline (at 5 m, as the national index measures it) (T-117)
    land = land_outline(bounds)
    from shapely import STRtree as _T
    from shapely.ops import unary_union as _U
    seas = sea_parts(P, geoms, WATER_PCT, land); waters += seas; n_sea = len(seas)
    print(n_sea, "parcels with sea drawn over them")
    nanv = [-1.0]   # water: no parcel
    for li, (side, tol) in enumerate(LEVELS):
        os.makedirs(os.path.join(OUT, "data", f"L{li}"))
        pieces, wet = {}, {}
        for pid, p in P.items():
            k = (int((p["rep_x"] - ORIGIN[0]) // side), int((p["rep_y"] - ORIGIN[1]) // side))
            pieces.setdefault(k, []).append(pid)
        for g in waters:   # water, simplified for this level; anything smaller than about a pixel there is left out
            if g.area < 4 * tol * tol: continue
            rp = g.representative_point(); k = (int((rp.x - ORIGIN[0]) // side), int((rp.y - ORIGIN[1]) // side))
            sg = g.simplify(tol, preserve_topology=True)
            if not sg.is_empty: wet.setdefault(k, []).append(sg); pieces.setdefault(k, [])
        index, total = {}, 0
        for (i, j), pids in sorted(pieces.items()):
            items, bb = [], [math.inf, math.inf, -math.inf, -math.inf]
            for pid in pids:
                p = P[pid]; g = level_shape(geoms.get(pid), p, tol)
                b = g.bounds; bb = [min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3])]
                v = [float(idx[pid])]   # the parcel's place in the value files (exact in float32 up to 16.7 million)
                items.append((pid, COUNCILS[p["c"]], v, g))   # water is drawn over parcels from the water layers, not by parcel
            for g in wet.get((i, j), []):
                b = g.bounds; bb = [min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3])]
                items.append((-1, WATER, nanv, g))
            blob = encode(items); key = f"{i}_{j}"
            open(os.path.join(OUT, "data", f"L{li}", key + ".bin"), "wb").write(blob)
            index[key] = [round(x) for x in bb] + [len(pids)]; total += len(blob)
            if li == 0 and pids:   # the side panel's values, in the same squares as full detail
                det = {str(pid): [clean(P[pid].get(f)) for f in DETAIL] for pid in pids}
                json.dump(det, open(os.path.join(OUT, "data", "detail", key + ".json"), "w"), separators=(",", ":"), ensure_ascii=False)
        meta["levels"].append(dict(side=side, tol=tol, pieces=index))
        print(f"level {li}: {len(index)} pieces, {total / 1e6:.1f} MB")
    srch = dict(id=[], x=[], y=[], t=[], c=[])
    for pid, p in P.items():
        srch["id"].append(pid); srch["x"].append(round(p["rep_x"])); srch["y"].append(round(p["rep_y"])); srch["c"].append(p["c"])
        srch["t"].append((p.get("appellation") or "") + ("|" + p["address"] if p.get("address") else ""))
    json.dump(srch, open(os.path.join(OUT, "data", "search.json"), "w"), separators=(",", ":"), ensure_ascii=False)
    json.dump(meta, open(os.path.join(OUT, "data", "meta.json"), "w"), separators=(",", ":"))
    here = os.path.dirname(os.path.abspath(__file__))
    shutil.copy(os.path.join(here, "map.html"), os.path.join(OUT, "index.html"))
    shutil.copy(os.path.join(here, "map.js"), os.path.join(OUT, "map.js"))
    shutil.copy(os.path.join(here, "vendor", "earcut-2.2.4.min.js"), os.path.join(OUT, "earcut.min.js"))
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    size = sum(os.path.getsize(os.path.join(a, f)) for a, _, fs in os.walk(OUT) for f in fs)
    print(f"site: {sum(len(fs) for _, _, fs in os.walk(OUT))} files, {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
