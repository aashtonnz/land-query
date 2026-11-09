"""Build the public map site (T-105, D-23, D-24) into a folder for GitHub Pages.

Usage: python3 site/build_map.py OUT_DIR. Reads the published results (`kapiti-results`, `porirua-results`, public-mode
columns only, D-12) and the national index pilot (`national-pilot`), and writes:

- index.html and map.js: the page (site/map.html, site/map.js);
- data/meta.json: council figures, the level and piece index, the coastline and the field lists;
- data/L{level}/{key}.bin: parcel shapes and colouring values, cut into squares at four levels of detail
  (LEVELS), so the page downloads only the pieces in view. At the simpler levels a parcel too small to keep its
  shape becomes a square of its own area at its point, so every parcel always covers its share of the land;
- data/detail/{key}.json: each parcel's values for the side panel, in the finest level's squares;
- data/search.json: legal descriptions and addresses for search.

Piece format (little-endian): "LQC1", parcels n, rings nr, vertices nv (uint32); ids (int32 × n); values (float32
× n × len(MEASURES), NaN for none); ring vertex counts (uint32 × nr, top bit set for a hole, which follows its outer
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
MEASURES = ["ground_mean_m", "slope_p90_deg", "catchment_area_max_m2", "ww_pipe_year"]
COUNCILS = {"k": 0, "p": 1, "n": 2}
WATER = 3   # council code for water (river and stream beds, lakes): drawn in the sea colour, never selected (id -1)
COUNCIL_COLS = ["unit_id", "appellation", "parcel_intent", "rep_x", "rep_y", "area_m2", "ground_mean_m", "slope_p90_deg",
                "lidar_coverage_pct", "flow_path_m", "catchment_area_max_m2", "title_count", "easements_n"]
KAPITI_ONLY = ["ww_pipe_dist_m", "ww_pipe_year", "ww_pipe_condition_grade", "ws_pipe_dist_m"]
DETAIL = ["c", "appellation", "parcel_intent", "area_m2", "ground_mean_m", "slope_p90_deg", "lidar_coverage_pct",
          "flow_path_m", "catchment_area_max_m2", "title_count", "easements_n", "building_cover_pct",
          "ww_pipe_dist_m", "ww_pipe_year", "ww_pipe_condition_grade", "ws_pipe_dist_m", "address", "territorial_authority"]


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
    for r in duckdb.sql(f"""SELECT parcel_id, appellation, parcel_intent, rep_x, rep_y, area_m2, ground_mean_m,
            upslope_area_max_m2, title_count, building_cover_pct, address, territorial_authority FROM '{nf}'""").fetchall():
        P[r[0]] = dict(c="n", appellation=r[1], parcel_intent=r[2], rep_x=r[3], rep_y=r[4], area_m2=r[5], ground_mean_m=r[6],
                       catchment_area_max_m2=r[7], title_count=r[8], building_cover_pct=r[9], address=r[10],
                       territorial_authority=r[11])
    n_all, nmed = duckdb.sql(f"SELECT count(*), round(median(ground_mean_m), 1) FROM '{nf}'").fetchall()[0]
    stats["n"] = dict(parcels=n_all, median_ground=nmed, run="national index pilot, built from " +
                      open(os.path.join(nd, "BUILT_FROM.txt")).read().strip())
    for c, council, branch, extra in [("k", "kapiti", "kapiti-results", KAPITI_ONLY), ("p", "porirua", "porirua-results", [])]:
        d = results(branch); pub = public_columns(council, d)
        cols = [x for x in COUNCIL_COLS + extra if x in pub]
        f = os.path.join(d, "units.parquet")
        for r in duckdb.sql(f"SELECT {', '.join(cols)} FROM '{f}'").fetchall():
            row = dict(zip(cols, r)); old = P.get(row["unit_id"], {})
            row.update(c=c, address=old.get("address"), territorial_authority=old.get("territorial_authority"))
            for k in ("rep_x", "rep_y", "area_m2"):
                if row.get(k) is None: row[k] = old.get(k)
            P[row.pop("unit_id")] = row
        n, lid, med = duckdb.sql(f"SELECT count(*), count(ground_mean_m), round(median(ground_mean_m), 1) FROM '{f}'").fetchall()[0]
        stats[c] = dict(parcels=n, with_lidar=lid, median_ground=med, run=open(os.path.join(d, "RUN.txt")).read().strip())
    shapes = {pid: b for pid, b in duckdb.sql(f"SELECT parcel_id, geometry_wkb FROM '{nf}'").fetchall()}
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
                       (svc + "NZ_Lake_Polygons_Topo_1_50k/FeatureServer/0", "1=1")]:
        for f in arcgis.query_all(url, dict(where=where, geometry=f"{x0},{y0},{x1},{y1}", geometryType="esriGeometryEnvelope", inSR=2193,
                                            spatialRel="esriSpatialRelIntersects", outFields="OBJECTID", outSR=2193, maxAllowableOffset=0.5), workers=8):
            if not f.get("geometry"): continue
            g = clip_by_rect(overlays.repaired(shape(f["geometry"])), x0, y0, x1, y1)
            if not g.is_empty and g.area > 0: out.append(g)
    return out


def main():
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "data", "detail"))
    P, shapes, stats = parcels()
    print(len(P), "parcels,", len(shapes), "shapes")
    geoms = {pid: wkb.loads(b) for pid, b in shapes.items()}
    xs = [p["rep_x"] for p in P.values()]; ys = [p["rep_y"] for p in P.values()]
    bounds = (min(xs) - 20000, min(ys) - 20000, max(xs) + 20000, max(ys) + 20000)
    meta = dict(origin=ORIGIN, levels=[], measures=MEASURES, councils=list(COUNCILS), detail_fields=DETAIL, stats=stats,
                bounds=bounds, parcels=len(P), land=coastline(bounds))
    waters = water(bounds); print(len(waters), "water polygons")
    nanv = [float("nan")] * len(MEASURES)
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
                v = [float(p[m]) if p.get(m) is not None else float("nan") for m in MEASURES]
                items.append((pid, COUNCILS[p["c"]], v, g))
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
