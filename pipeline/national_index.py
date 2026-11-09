"""National index (T-100, D-21): one row per parcel anywhere in New Zealand, from LINZ data only.

Tier 1 of the national MVP (docs/proposals/2026-11-09-national-mvp.md). Built tile by tile (40 km squares on the
NZTM grid) so the same code runs for one region or the whole country. For each tile:

- parcels: LINZ NZ Primary Parcels whose representative point lies in the tile (each parcel in exactly one tile),
  without road, water and seabed parcels (EXCLUDE_INTENTS);
- vector columns (vector_columns): area and shape, titles and their types, LINZ building outlines, addresses, road
  frontage (boundary shared with road parcels) and distance to the coast (mean high water springs);
- elevation columns (elevation_columns): from LINZ's national 1 m DEM read at 10 m, gaps filled from the 8 m contour
  DEM (district_flow.mosaic), over the tile plus MARGIN: ground height, slope, flat, steep and low-lying shares, the
  share from LiDAR, and the largest upslope area (D8), flagged when it may reach past the margin.

Vector data comes from LINZ's own public ArcGIS services (no key), each the same dataset as the LINZ Data Service
layer named in LAYERS, under CC BY 4.0. Nothing about owners is read (D-12, D-15).

Usage: national_index.py OUT_DIR [REGION]. REGION is a key of REGIONS (default: wellington). Writes OUT_DIR/index.parquet,
OUT_DIR/provenance.json and OUT_DIR/run.json (time and size); raw downloads are cached under OUT_DIR/cache.
"""
import datetime as dt, gzip, hashlib, json, math, os, sys, time
import numpy as np, pandas as pd
from shapely import STRtree, wkb
from shapely.geometry import shape, box
from shapely.ops import unary_union

import arcgis
import overlays as ov
from provenance import utc_now

SVC = "https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services/"
LDS = "https://data.linz.govt.nz/layer/"
LICENCE = "LINZ, CC BY 4.0"
# name: (service, fields, LINZ Data Service layer)
LAYERS = dict(
    parcels=("LINZ_NZ_Primary_Parcels", "id,appellation,parcel_intent,topology_type,statutory_actions,land_district,titles,survey_area,calc_area", 50823),
    titles=("LINZ_NZ_Property_Titles", "title_no,status,type", 50804),          # never owners or number_owners
    buildings=("LINZ_NZ_Building_Outlines", "building_id,use_,capture_source_to", 101290),
    addresses=("LINZ_NZ_Addresses", "address_id,full_address,address_number,suburb_locality,town_city,territorial_authority", 105689),
    coast=("LINZ_NZ_Coastline_Mean_High_Water_Springs", "id", None),            # LDS layer number to confirm
)
KEYS = dict(parcels="id", titles="title_no", buildings="building_id", addresses="address_id", coast="id")
EXCLUDE_INTENTS = ov.NOT_PRIMARY_INTENTS | {"Common Marine and Coastal Area (Sec 237A(1)(b) RM Act)"}
TILE = 40000.0
ORIGIN = (1000000.0, 4700000.0)
MARGIN = 5000.0          # elevation read this far beyond the tile, so catchments are whole for nearly every parcel
COAST_MAX = 10000.0      # coast distance searched to here; beyond it the distance is left empty and coast_over_10km set
RES = 10.0
WORKERS = 8           # pages fetched in parallel from LINZ's services
FLAT_DEG, STEEP_DEG, LOW_M = 5.0, 15.0, 5.0

GW_TA = "https://mapping.gw.govt.nz/arcgis/rest/services/Region_basemap_P/MapServer/1"
REGIONS = dict(wellington=dict(
    name="Greater Wellington (its eight districts and cities; the small part of Tararua District in the region is left out)",
    url=GW_TA, where="1=1", licence="Stats NZ district polygons, CC BY 4.0, via GWRC"))


def tiles_for(bounds):
    """Tile boxes (x0, y0, x1, y1) covering bounds."""
    i0, i1 = int((bounds[0] - ORIGIN[0]) // TILE), int((bounds[2] - ORIGIN[0]) // TILE)
    j0, j1 = int((bounds[1] - ORIGIN[1]) // TILE), int((bounds[3] - ORIGIN[1]) // TILE)
    return [(ORIGIN[0] + i * TILE, ORIGIN[1] + j * TILE, ORIGIN[0] + (i + 1) * TILE, ORIGIN[1] + (j + 1) * TILE)
            for j in range(j0, j1 + 1) for i in range(i0, i1 + 1)]


def in_tile(pt, t):
    """Half-open, so a point on a shared edge belongs to one tile only."""
    return t[0] <= pt.x < t[2] and t[1] <= pt.y < t[3]


def fetch(layer, bbox, cache, where="1=1"):
    """GeoJSON features of a LINZ layer intersecting bbox, cached gzipped; (features, provenance entry)."""
    svc, fields, lds = LAYERS[layer]
    key = hashlib.sha256(json.dumps([layer, [round(v) for v in bbox], where]).encode()).hexdigest()[:16]
    path = os.path.join(cache, f"{layer}-{key}.json.gz")
    if os.path.exists(path):
        d = json.load(gzip.open(path, "rt"))
    else:
        t0 = time.time()
        feats = arcgis.query_all(SVC + svc + "/FeatureServer/0", dict(
            where=where, geometry=",".join(str(round(v)) for v in bbox), geometryType="esriGeometryEnvelope", inSR=2193,
            spatialRel="esriSpatialRelIntersects", outFields=fields, outSR=2193), workers=WORKERS)
        d = dict(features=feats, fetched=utc_now(), seconds=round(time.time() - t0, 1))
        os.makedirs(cache, exist_ok=True)
        json.dump(d, gzip.open(path + ".tmp", "wt")); os.replace(path + ".tmp", path)
    feats, repeats, differ = once_each(d["features"], KEYS[layer])
    return feats, dict(url=SVC + svc + "/FeatureServer/0", same_as=(LDS + str(lds)) if lds else None,
                       features=len(feats), repeated_records=repeats, repeated_with_other_values=differ,
                       fetched=d["fetched"], licence=LICENCE)


def once_each(feats, key):
    """(features with one record per key, records dropped, of those how many had other attribute values). LINZ's
    ArcGIS copies hold some parcels and buildings twice: parcels with the same values and shapes differing by under
    0.1 m² (1,368 in Wellington City), buildings with the same shape, one copy's use_ "Unknown" and the other's empty
    (433 in Greater Wellington; T-100). The first record is kept."""
    seen, out, repeats, differ = {}, [], 0, 0
    for f in feats:
        k = f["properties"].get(key)
        if k is None: out.append(f); continue
        if k in seen:
            repeats += 1; differ += seen[k]["properties"] != f["properties"]
            continue
        seen[k] = f; out.append(f)
    return out, repeats, differ


def geoms(feats):
    out = []
    for f in feats:
        if not f.get("geometry"): continue
        g = shape(f["geometry"])
        out.append((ov.repaired(g) if g.geom_type in ("Polygon", "MultiPolygon") else g, f["properties"]))
    return out


def select_parcels(feats, tile, region=None):
    """[(geometry, properties, representative point)] of the tile's own parcels."""
    out = []
    for g, p in geoms(feats):
        if p.get("parcel_intent") in EXCLUDE_INTENTS or g.is_empty: continue
        rp = g.representative_point()
        if in_tile(rp, tile) and (region is None or region.contains(rp)):
            out.append((g, p, rp))
    return out


def _date(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date().isoformat() if ms else None


def vector_columns(parcels, roads, titles, buildings, addresses, coast, tas=()):
    """One dict per parcel. parcels: [(geometry, properties, representative point)]; roads, buildings, addresses, coast,
    tas: [(geometry, properties)]; titles: {title_no: properties}."""
    bt = STRtree([g for g, _ in buildings]) if buildings else None
    at = STRtree([g for g, _ in addresses]) if addresses else None
    road_buf = [g.buffer(1.0) for g, _ in roads]
    rt = STRtree(road_buf) if road_buf else None
    ct = STRtree([g for g, _ in coast]) if coast else None
    tt = STRtree([g for g, _ in tas]) if tas else None
    rows = []
    for g, p, rp in parcels:
        a, per = g.area, g.length
        mrr = g.minimum_rotated_rectangle
        sides = [math.dist(*c) for c in zip(mrr.exterior.coords, list(mrr.exterior.coords)[1:])] if mrr.geom_type == "Polygon" else [0.0]
        tnos = [t.strip() for t in (p.get("titles") or "").split(",") if t.strip()]
        ttypes = sorted({titles[t]["type"] for t in tnos if t in titles and titles[t].get("type")})
        r = dict(parcel_id=p.get("id"), appellation=p.get("appellation"), parcel_intent=p.get("parcel_intent"),
                 land_district=p.get("land_district"), statutory_actions=p.get("statutory_actions"),
                 area_m2=round(a, 1), survey_area_m2=p.get("survey_area"), perimeter_m=round(per, 1),
                 compactness=round(4 * math.pi * a / per ** 2, 3) if per else None,
                 width_m=round(min(sides), 1) if sides else None,
                 title_count=len(tnos), title_types=", ".join(ttypes) or None,
                 titles_not_found=sum(t not in titles for t in tnos),
                 rep_x=round(rp.x, 1), rep_y=round(rp.y, 1))
        # buildings: area of outlines inside the parcel; a building is counted where at least half of it is inside
        bm2, n, big, cap = 0.0, 0, 0.0, None
        for i in (bt.query(g) if bt else []):
            b, bp = buildings[i]
            ia = g.intersection(b).area
            if ia <= 0: continue
            bm2 += ia
            if ia >= 0.5 * b.area: n += 1; big = max(big, b.area)
            cap = max(cap or 0, bp.get("capture_source_to") or 0) or cap
        r.update(building_count=n, building_m2=round(bm2, 1), building_cover_pct=round(100 * bm2 / a, 1) if a else None,
                 largest_building_m2=round(big, 1) if n else None, buildings_captured_to=_date(cap))
        # addresses whose point lies in the parcel; the lowest number names it
        ads = [addresses[i][1] for i in (at.query(g, predicate="contains") if at else [])]
        ads.sort(key=lambda q: (q.get("address_number") or 0, q.get("full_address") or ""))
        r.update(address_count=len(ads), address=ads[0]["full_address"] if ads else None,
                 suburb_locality=ads[0].get("suburb_locality") if ads else None, town_city=ads[0].get("town_city") if ads else None)
        ta = [tas[i][1].get("NAME") for i in (tt.query(rp, predicate="within") if tt else [])]
        r["territorial_authority"] = ta[0] if ta else (ads[0].get("territorial_authority") if ads else None)
        # road frontage: the parcel's boundary within 1 m of a road parcel
        near = [road_buf[i] for i in (rt.query(g) if rt else [])]
        r["road_frontage_m"] = round(g.boundary.intersection(unary_union(near)).length, 1) if near else 0.0
        if ct is not None:
            idx, dist = ct.query_nearest(g, max_distance=COAST_MAX, return_distance=True)
            d = float(dist.min()) if len(dist) else None
        else:
            d = None
        r.update(coast_distance_m=round(d, 1) if d is not None else None, coast_over_10km=d is None)
        rows.append(r)
    return rows


def slope_deg(Z, res=RES):
    gy, gx = np.gradient(Z, res)
    return np.degrees(np.arctan(np.hypot(gx, gy))).astype(np.float32)


def elevation_columns(parcels, Z, T, lidar, acc, trunc):
    """One dict per parcel from 10 m grids (Z ground, lidar mask, acc upslope area m², trunc flag), aligned to T. A
    parcel too small to hold a cell centre is read at its representative point (elevation_from 'point')."""
    from rasterio.features import rasterize
    H, W = Z.shape
    lab = rasterize(((g, i + 1) for i, (g, _, _) in enumerate(parcels)), out_shape=(H, W), transform=T, fill=0, dtype="int32")
    S = slope_deg(Z)
    m = (lab > 0) & np.isfinite(Z)
    df = pd.DataFrame(dict(l=lab[m], z=Z[m], s=S[m], li=lidar[m], acc=acc[m], tr=trunc[m]))
    df["flat"], df["steep"], df["low"] = df.s < FLAT_DEG, df.s > STEEP_DEG, df.z < LOW_M
    g = df.groupby("l")
    agg = g.agg(n=("z", "size"), zm=("z", "mean"), z0=("z", "min"), z1=("z", "max"), sm=("s", "mean"), s1=("s", "max"),
                flat=("flat", "mean"), steep=("steep", "mean"), low=("low", "mean"), li=("li", "mean"))
    top = df.sort_values("acc").groupby("l").tail(1).set_index("l")
    allc = np.bincount(lab.ravel(), minlength=len(parcels) + 1)
    rows = []
    for i, (geom, _, rp) in enumerate(parcels):
        k = i + 1
        if k in agg.index:
            a = agg.loc[k]
            rows.append(dict(ground_mean_m=round(a.zm, 1), ground_min_m=round(a.z0, 1), ground_max_m=round(a.z1, 1),
                             slope_mean_deg=round(a.sm, 1), slope_max_deg=round(a.s1, 1), flat_pct=round(100 * a.flat, 1),
                             steep_pct=round(100 * a.steep, 1), low_lying_pct=round(100 * a.low, 1),
                             lidar_pct=round(100 * a.li, 1), ground_cells=int(a.n),
                             ground_cells_pct=round(100 * a.n / max(allc[k], geom.area / RES ** 2), 1),   # under 100: no ground, or past the grid
                             upslope_area_max_m2=float(round(top.loc[k, "acc"])), upslope_truncated=bool(top.loc[k, "tr"]),
                             elevation_from="cells"))
            continue
        c, r = ~T * (rp.x, rp.y)
        r, c = int(r), int(c)
        ok = allc[k] == 0 and 0 <= r < H and 0 <= c < W and np.isfinite(Z[r, c])
        rows.append(dict(ground_mean_m=round(float(Z[r, c]), 1) if ok else None,
                         ground_min_m=None, ground_max_m=None,
                         slope_mean_deg=round(float(S[r, c]), 1) if ok and np.isfinite(S[r, c]) else None, slope_max_deg=None,
                         flat_pct=None, steep_pct=None, low_lying_pct=None,
                         lidar_pct=(100.0 if lidar[r, c] else 0.0) if ok else None, ground_cells=0, ground_cells_pct=0.0,
                         upslope_area_max_m2=float(round(acc[r, c])) if ok and np.isfinite(acc[r, c]) else None,
                         upslope_truncated=bool(trunc[r, c]) if ok else None, elevation_from="point" if ok else None))
    return rows


def elevation_grid(tile):
    """Ground, transform, provenance, LiDAR mask, upslope area and truncation over the tile plus MARGIN."""
    import district_flow as DF, flow
    bb = (tile[0] - MARGIN, tile[1] - MARGIN, tile[2] + MARGIN, tile[3] + MARGIN)
    Z, T, prov, L = DF.mosaic(bbox=bb, res=RES, lidar_mask=True)
    edge = np.zeros(Z.shape, bool); edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True  # the sea is an outlet
    acc, tr, _ = flow.flow_routing(Z, T, inflow=edge) if np.isfinite(Z).any() else (np.full(Z.shape, np.nan), np.zeros(Z.shape, bool), None)
    return Z, T, prov, L, acc, tr


def index_tile(tile, cache, region=None, tas=()):
    """(rows, provenance) for one tile."""
    t0 = time.time()
    pf, pp = fetch("parcels", tile, cache)
    parcels = select_parcels(pf, tile, region)
    prov = dict(tile=list(tile), parcels=pp)
    if not parcels: return [], dict(prov, rows=0, seconds=round(time.time() - t0, 1))
    bs = np.array([g.bounds for g, _, _ in parcels])
    win = (bs[:, 0].min() - 30, bs[:, 1].min() - 30, bs[:, 2].max() + 30, bs[:, 3].max() + 30)
    rf, prov["roads"] = fetch("parcels", win, cache, where="parcel_intent='Road'")
    tf, prov["titles"] = fetch("titles", win, cache)
    bf, prov["buildings"] = fetch("buildings", win, cache)
    af, prov["addresses"] = fetch("addresses", win, cache)
    cf, prov["coast"] = fetch("coast", (win[0] - COAST_MAX, win[1] - COAST_MAX, win[2] + COAST_MAX, win[3] + COAST_MAX), cache)
    titles = {f["properties"]["title_no"]: f["properties"] for f in tf if f["properties"].get("status") == "LIVE"}
    rows = vector_columns(parcels, geoms(rf), titles, geoms(bf), geoms(af), geoms(cf), tas)
    t1 = time.time()
    Z, T, eprov, L, acc, tr = elevation_grid(tile)
    for r, e in zip(rows, elevation_columns(parcels, Z, T, L, acc, tr)): r.update(e)
    for r, (g, _, _) in zip(rows, parcels):
        r["geometry_wkb"] = wkb.dumps(g.simplify(0.5, preserve_topology=True))
    prov.update(elevation=eprov, rows=len(rows), seconds_vector=round(t1 - t0, 1), seconds_elevation=round(time.time() - t1, 1))
    return rows, prov


def region_shapes(key):
    R = REGIONS[key]
    feats = arcgis.query_all(R["url"], dict(where=R["where"], outFields="NAME", outSR=2193))
    tas = [(ov.repaired(shape(f["geometry"])), f["properties"]) for f in feats if f.get("geometry")]
    return unary_union([g for g, _ in tas]), tas, dict(url=R["url"], features=len(feats), licence=R["licence"],
                                                     fetched=utc_now(), name=R["name"])


if __name__ == "__main__":
    out = sys.argv[1]; key = sys.argv[2] if len(sys.argv) > 2 else "wellington"
    os.makedirs(out, exist_ok=True); cache = os.path.join(out, "cache")
    t0 = time.time()
    region, tas, rprov = region_shapes(key)
    tiles = [t for t in tiles_for(region.bounds) if region.intersects(box(*t))]
    rows, tprov = [], []
    for i, t in enumerate(tiles):
        r, p = index_tile(t, cache, region, tas)
        rows += r; tprov.append(p)
        print(f"tile {i + 1}/{len(tiles)} {t}: {len(r)} parcels, {p.get('seconds_vector', p.get('seconds'))}s vector, "
              f"{p.get('seconds_elevation', 0)}s elevation", flush=True)
    df = pd.DataFrame(rows)
    path = os.path.join(out, "index.parquet")
    df.to_parquet(path, index=False, compression="zstd")
    json.dump(dict(region=rprov, tiles=tprov, built=utc_now(), commit=os.environ.get("GITHUB_SHA")),
              open(os.path.join(out, "provenance.json"), "w"), indent=1)
    run = dict(region=key, parcels=len(df), tiles=len(tiles), seconds=round(time.time() - t0),
               index_mb=round(os.path.getsize(path) / 1e6, 1),
               duplicate_ids=int(df.parcel_id.duplicated().sum()) if len(df) else 0)
    json.dump(run, open(os.path.join(out, "run.json"), "w"), indent=1)
    print(json.dumps(run))
