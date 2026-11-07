"""Raw-source sample check (T-45): recompute key values for named parcels straight from the sources.

Deliberately independent of the pipeline's code: overlays come from the council servers' own spatial queries against
the parcel polygon, the nearest manhole from a server-side distance query, and ground levels from the LINZ LiDAR files
read directly. Each value is compared with the compiled district results.

Usage: sample_check.py UNITS_PARQUET OUT_JSON UNIT_ID [UNIT_ID ...]
"""
import json, sys
import duckdb, numpy as np, rasterio, requests
from rasterio.mask import mask as rmask
from shapely.geometry import shape, mapping
from pyproj import Transformer

KC = "https://maps.kapiticoast.govt.nz/server/rest/services/Public"
LAYERS = {  # compiled column: (layer URL, class field)
    "ovl_flood_hazard": (f"{KC}/District_Plan_Overlays/MapServer/11", "ZONE"),
    "flood_ponding": (f"{KC}/Latest_Flood_Hazards/MapServer/6", "ZONE"),
    "flood_storage": (f"{KC}/Latest_Flood_Hazards/MapServer/5", "ZONE"),
    "flood_residual_ponding": (f"{KC}/Latest_Flood_Hazards/MapServer/7", "ZONE"),
    "tsunami_zones": (f"{KC}/Tsunami/MapServer/3", "Evac_Zone"),
    "ovl_coastal_env": (f"{KC}/District_Plan_Overlays/MapServer/30", None),
    "gw_liquefaction": ("https://mapping.gw.govt.nz/arcgis/rest/services/GW/Emergencies_P/MapServer/10", "Liquefaction"),
}
LIDAR = "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/wellington/kapiti-coast_2024-2025/dem_1m/2193/"


def get(url, **params):
    # queries go by POST: a large parcel's polygon is too long for a URL
    r = (requests.post(url, data=params, timeout=120) if url.endswith("/query") else requests.get(url, params=params, timeout=120))
    r.raise_for_status(); j = r.json()
    if "error" in j: raise RuntimeError(j["error"])
    return j


def esri_polygon(g):
    rings = [list(map(list, p.exterior.coords)) for p in (g.geoms if g.geom_type == "MultiPolygon" else [g])]
    return json.dumps({"rings": rings, "spatialReference": {"wkid": 2193}})


def parcel(uid):
    j = get(f"{KC}/Cadastral/MapServer/0/query", where=f"id={uid}", outFields="id,appellation", outSR=2193, f="geojson")
    f = j["features"][0]
    return shape(f["geometry"]), f["properties"]


def zones(g):
    """Zone shares from the raw zone polygons: union per operative zone, intersected with the parcel."""
    from shapely.ops import unary_union
    j = get(f"{KC}/District_Plan_Zones/MapServer/0/query", geometry=esri_polygon(g), geometryType="esriGeometryPolygon",
            inSR=2193, spatialRel="esriSpatialRelIntersects", outFields="ePlan_Zone", outSR=2193, f="geojson")
    by = {}
    for f in j["features"]: by.setdefault(f["properties"]["ePlan_Zone"], []).append(shape(f["geometry"]).buffer(0))
    out = {k: round(100 * unary_union(v).intersection(g).area / g.area, 1) for k, v in by.items()}
    return {k: v for k, v in out.items() if v * g.area / 100 > 0.5}


def overlay(url, field, g):
    """Classes of a layer whose features overlap the parcel by more than 0.5 m² (as the compiler counts them)."""
    j = get(url + "/query", geometry=esri_polygon(g), geometryType="esriGeometryPolygon", inSR=2193,
            spatialRel="esriSpatialRelIntersects", outFields=field or "OBJECTID", outSR=2193, f="geojson")
    return sorted({(f["properties"].get(field) if field else "present") for f in j["features"]
                   if shape(f["geometry"]).buffer(0).intersection(g).area > 0.5})


def nearest_manhole(g, maxd=150):
    c = g.buffer(maxd).bounds
    j = get(f"{KC}/Services_Open_Data/MapServer/9/query", geometry=",".join(map(str, c)), geometryType="esriGeometryEnvelope",
            inSR=2193, where="status='INUS' AND node_type='WWMH' AND invert_level_nzvd2016 IS NOT NULL",
            outFields="asset_id,invert_level_nzvd2016", outSR=2193, f="geojson")
    best = min(((shape(f["geometry"]).distance(g), f["properties"]) for f in j["features"]), default=None, key=lambda t: t[0])
    return None if best is None or best[0] > maxd else dict(id=best[1]["asset_id"], dist=round(best[0], 1), invert=best[1]["invert_level_nzvd2016"])


def points_inside(layer, idf, g):
    j = get(f"{KC}/District_Plan_Overlays/MapServer/{layer}/query", geometry=esri_polygon(g), geometryType="esriGeometryPolygon",
            inSR=2193, spatialRel="esriSpatialRelIntersects", outFields=idf, f="json")
    return sorted(str(f["attributes"][idf]) for f in j["features"])


_items = None
def ground(g):
    """Mean and minimum LiDAR ground on the parcel from the 2024-25 DEM sheets, read directly."""
    global _items
    if _items is None:
        c = get(LIDAR + "collection.json"); tr = Transformer.from_crs(4326, 2193, always_xy=True); _items = []
        for l in c["links"]:
            if l["rel"] != "item": continue
            it = get(LIDAR + l["href"].lstrip("./")); w, s, e, n = it["bbox"]
            xs, ys = tr.transform([w, e, w, e], [s, s, n, n])
            _items.append(((min(xs), min(ys), max(xs), max(ys)), LIDAR + it["assets"]["visual"]["href"].lstrip("./")))
    vals = []
    for (x0, y0, x1, y1), href in _items:
        b = g.bounds
        if b[0] > x1 or b[2] < x0 or b[1] > y1 or b[3] < y0: continue
        with rasterio.open(href) as d:
            try: a, _ = rmask(d, [mapping(g)], crop=True, filled=False)
            except ValueError: continue
            v = a[0].compressed(); vals.append(v[np.isfinite(v) & (v > -1000)])
    v = np.concatenate(vals) if vals else np.array([])
    return None if v.size == 0 else dict(mean=round(float(v.mean()), 2), min=round(float(v.min()), 2), cells=int(v.size))


def check(uid, row):
    g, props = parcel(uid)
    out = dict(unit_id=uid, appellation=props.get("appellation"), checks={})
    C = out["checks"]
    C["area_m2"] = dict(raw=round(g.area, 1), compiled=row["area_m2"], ok=abs(g.area - row["area_m2"]) < 1)
    z = zones(g); zc = json.loads(row["zones"]) if row["zones"] else {}
    C["zones"] = dict(raw=z, compiled=zc, ok=set(z) == set(zc) and all(abs(z[k] - zc[k]) <= 0.2 for k in z))
    for col, (url, field) in LAYERS.items():
        raw = overlay(url, field, g); comp = sorted(json.loads(row[col])) if row.get(col) else []
        if field is None: comp = ["present"] if comp else []
        C[col] = dict(raw=raw, compiled=comp, ok=raw == comp)
    mh = nearest_manhole(g)
    C["ww_mh"] = dict(raw=mh, compiled=dict(id=row["ww_mh_id"], dist=row["ww_mh_dist_m"], invert=row["ww_mh_invert_nzvd2016"]),
                      ok=(mh is None and row["ww_mh_id"] is None) or (mh is not None and mh["id"] == row["ww_mh_id"] and abs(mh["dist"] - row["ww_mh_dist_m"]) < 0.2))
    for col, layer, idf in (("ovl_heritage_places", 14, "BUILDING_ID"), ("ovl_notable_trees", 16, "TREE_ID")):
        raw = points_inside(layer, idf, g); comp = sorted(str(p["id"]) for p in json.loads(row[col] or "[]"))
        C[col] = dict(raw=raw, compiled=comp, ok=raw == comp)
    gr = ground(g)
    if gr is None: C["ground"] = dict(raw=None, compiled=row["ground_mean_m"], ok=row["ground_mean_m"] is None)
    else:
        C["ground"] = dict(raw=gr, compiled=dict(mean=row["ground_mean_m"], min=row["ground_min_m"], cells=row["lidar_cells"]),
                           ok=row["ground_mean_m"] is not None and abs(gr["mean"] - row["ground_mean_m"]) <= 0.05 and abs(gr["min"] - row["ground_min_m"]) <= 0.05)
    out["all_ok"] = all(c["ok"] for c in C.values())
    return out


if __name__ == "__main__":
    units, outp, ids = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]]
    db = duckdb.connect()
    res = []
    for uid in ids:
        cur = db.execute(f"SELECT * FROM read_parquet('{units}') WHERE unit_id = ?", [uid])
        cols = [c[0] for c in cur.description]; r = cur.fetchone()
        if r is None: res.append(dict(unit_id=uid, error="not in compiled results")); continue
        try: res.append(check(uid, dict(zip(cols, r))))
        except Exception as e: res.append(dict(unit_id=uid, error=str(e)[:300]))
        x = res[-1]
        print(uid, x.get("appellation"), "OK" if x.get("all_ok") else "DIFF: " + ", ".join(k for k, v in x.get("checks", {}).items() if not v["ok"]) or x.get("error"))
    json.dump(res, open(outp, "w"), indent=1, default=str)
