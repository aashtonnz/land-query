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
    parcels=("LINZ_NZ_Primary_Parcels", "id,appellation,parcel_intent,topology_type,land_district,titles,survey_area,calc_area", 50823),
    titles=("LINZ_NZ_Property_Titles", "title_no,status,type", 50804),          # never owners or number_owners
    buildings=("LINZ_NZ_Building_Outlines", "building_id,use_,capture_source_to", 101290),
    addresses=("LINZ_NZ_Addresses", "address_id,full_address,address_number,suburb_locality,town_city,territorial_authority", 105689),
    coast=("LINZ_NZ_Coastline_Mean_High_Water_Springs", "id", None),            # LDS layer number to confirm
    lakes=("NZ_Lake_Polygons_Topo_1_50k", "t50_fid", None),                     # Topo50 lakes (T-113)
    rivers=("LINZ_NZ_River_Name_Polygons_Pilot", "river_section_id", None),     # river areas (T-113)
    land=("LINZ_NZ_Coastline", "id", None),                                     # land outline (Topo50): the sea is outside it (T-115)
)
KEYS = dict(parcels="id", titles="title_no", buildings="building_id", addresses="address_id", coast="id", lakes="t50_fid", rivers=None, land="id")
EXCLUDE_INTENTS = ov.NOT_PRIMARY_INTENTS | {"Common Marine and Coastal Area (Sec 237A(1)(b) RM Act)", "Riverbed", "Streambed"}
# a parcel belongs to a region if its point lies within this distance of the region's boundary polygons, which follow
# a simplified coast: shore and island parcels fell just outside (T-108)
REGION_MARGIN = 1000.0
COAST_BAND = 300.0
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


# the land outline is a few very large polygons: the service limits those per minute, so one request at a time,
# simplified to 5 m: well within its 1:50k accuracy (about 25 m), and 9 s a tile rather than minutes (T-115)
FETCH_OPTS = dict(land=dict(workers=1, maxAllowableOffset=5))


def fetch(layer, bbox, cache, where="1=1"):
    """GeoJSON features of a LINZ layer intersecting bbox, cached gzipped; (features, provenance entry)."""
    svc, fields, lds = LAYERS[layer]
    # the fetch options (detail) are part of the key, so a cached download is never reused at another detail (T-117)
    key = hashlib.sha256(json.dumps([layer, [round(v) for v in bbox], where, FETCH_OPTS.get(layer, {})], sort_keys=True).encode()).hexdigest()[:16]
    path = os.path.join(cache, f"{layer}-{key}.json.gz")
    if os.path.exists(path):
        d = json.load(gzip.open(path, "rt"))
    else:
        t0 = time.time()
        feats = arcgis.query_all(SVC + svc + "/FeatureServer/0", dict(
            where=where, geometry=",".join(str(round(v)) for v in bbox), geometryType="esriGeometryEnvelope", inSR=2193,
            spatialRel="esriSpatialRelIntersects", outFields=fields, outSR=2193,
            **{k: v for k, v in FETCH_OPTS.get(layer, {}).items() if k != "workers"}), workers=FETCH_OPTS.get(layer, {}).get("workers", WORKERS))
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
        if in_tile(rp, tile) and (region is None or region.contains(rp)):   # region: already grown by REGION_MARGIN
            out.append((g, p, rp))
    return out


def current_titles(feats):
    """{title number: properties} of current titles: live, and partly cancelled (PRTC), which still apply to the land
    that remains (T-108)."""
    return {f["properties"]["title_no"]: f["properties"] for f in feats if f["properties"].get("status") in ("LIVE", "PRTC")}


def _date(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).date().isoformat() if ms else None


def frontage(g, own_id, road_tree, road_buf, nb_tree, nb):
    """Length of g's boundary within 1 m of a road parcel (road parcels often sit 0.2-0.4 m off the lot line), less the
    short pieces, up to 1.5 m, where a side boundary with another land parcel runs into the road: the ends of the
    frontage. Longer stretches are kept, so messy surveys (a road a little off a lot's side, a thin reserve strip
    between lot and road) can lengthen a frontage but never empty it (T-111, T-112)."""
    near = [road_buf[i] for i in (road_tree.query(g) if road_tree else [])]
    if not near: return 0.0, 0.0
    edge = g.boundary.intersection(unary_union(near))
    sides = [q for q in (nb[i][0] for i in (nb_tree.query(g.buffer(0.2)) if nb_tree else []) if nb[i][1] != own_id)]
    # each neighbour separately: one that shares only an end piece is a side; one sharing more (a strip along the
    # frontage) is not
    ends = [piece for piece in (edge.intersection(q.buffer(0.1)) for q in sides) if 0 < piece.length <= 1.5]
    if ends: edge = edge.difference(unary_union([x.buffer(0.01) for x in ends]))
    # the part reached only across a strip under 1 m wide (often a reserve that bars access): reported apart (T-113)
    thin = [q for q in sides if q.length and 2 * q.area / q.length < 1.0]
    via = edge.intersection(unary_union([q.buffer(0.1) for q in thin])).length if thin else 0.0
    return round(edge.length, 1), round(via, 1)


def water_shares(parcels, water, land):
    """Share (%) of each parcel under water, measured by area: the union of lake and river polygons and the sea, which
    is everything outside the land outline. A part both lake and sea counts once; no elevation grid is involved, so
    missing elevation data can never read as water (T-115)."""
    wt = STRtree([g for g, _ in water]) if water else None
    lt = STRtree([g for g, _ in land]) if land else None
    out = []
    for g, _, _ in parcels:
        if not g.area: out.append(None); continue
        on_land = unary_union([land[i][0] for i in lt.query(g)]) if lt is not None else None
        sea = g.difference(on_land) if on_land is not None and not on_land.is_empty else g
        wet = [water[i][0] for i in wt.query(g)] if wt is not None else []
        allw = unary_union([sea] + [g.intersection(w) for w in wet])
        out.append(round(min(100.0, 100 * allw.area / g.area), 1))
    return out


def vector_columns(parcels, roads, titles, buildings, addresses, coast, tas=(), neighbours=()):
    """One dict per parcel. parcels: [(geometry, properties, representative point)]; roads, buildings, addresses, coast,
    tas: [(geometry, properties)]; titles: {title_no: properties}."""
    bt = STRtree([g for g, _ in buildings]) if buildings else None
    at = STRtree([g for g, _ in addresses]) if addresses else None
    road_buf = [g.buffer(1.0) for g, _ in roads]
    nb = [(g, p.get("id")) for g, p in neighbours]; nt = STRtree([g for g, _ in nb]) if nb else None
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
                 land_district=p.get("land_district"),
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
        # road frontage: the parcel's boundary within 0.1 m of a road parcel
        r["road_frontage_m"], r["road_frontage_via_strip_m"] = frontage(g, p.get("id"), rt, road_buf, nt, nb)
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
                             ground_cells_pct=round(100 * a.n / max(1, allc[k]), 1),   # of the parcel's own cell centres: under 100 means some have no ground (T-108)
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
    # partly cancelled titles (PRTC) are still current for the land that remains (T-108)
    titles = current_titles(tf)
    neighbours = [(g, p) for g, p in geoms(pf) if p.get("parcel_intent") != "Road"]
    rows = vector_columns(parcels, geoms(rf), titles, geoms(bf), geoms(af), geoms(cf), tas, neighbours)
    # water is measured, never guessed from a name or a title (T-113, T-115)
    lw = geoms(fetch("lakes", win, cache)[0]) + geoms(fetch("rivers", win, cache)[0])
    lf, prov["land"] = fetch("land", win, cache)
    prov["land"]["max_allowable_offset_m"] = FETCH_OPTS["land"]["maxAllowableOffset"]
    prov["lakes_rivers"] = len(lw)
    # no land outline here (LINZ's has nothing east of 2,480,000 E, e.g. the Chatham islets): the sea share is unknown, so
    # water_pct is empty, not 100 (T-117)
    if not lf:
        prov["land"]["missing"] = True
        for r in rows: r["water_pct"] = None
    from shapely import clip_by_rect
    land = [(clip_by_rect(g, *win), p) for g, p in geoms(lf)]   # only this tile's part of the North Island outline
    if lf:
        for r, s_ in zip(rows, water_shares(parcels, lw, [(g, p) for g, p in land if not g.is_empty])): r["water_pct"] = s_
    # a parcel taken in by the coastal margin is left out only on positive evidence that it is another district's: its
    # own address, or else the nearest address within 1 km. With no address near (islands), it stays (T-111, T-115)
    if REGION_NAMES:
        adr = geoms(af); at = STRtree([g for g, _ in adr]) if adr else None
        def district(k):
            if rows[k].get("territorial_authority"): return rows[k]["territorial_authority"]
            if at is None: return None
            i_, d_ = at.query_nearest(parcels[k][2], max_distance=1000, return_distance=True)
            return adr[int(i_[0])][1].get("territorial_authority") if len(i_) else None
        keep = [k for k in range(len(rows)) if parcels[k][2].within(REGION_CORE) or (lambda d: d is None or plain(d) in REGION_NAMES)(district(k))]
        prov["outside_region_by_address"] = len(rows) - len(keep)
        rows = [rows[k] for k in keep]; parcels = [parcels[k] for k in keep]
    if not rows: return [], dict(prov, rows=0, seconds=round(time.time() - t0, 1))
    t1 = time.time()
    Z, T, eprov, L, acc, tr = elevation_grid(tile)
    for r, e in zip(rows, elevation_columns(parcels, Z, T, L, acc, tr)): r.update(e)
    for r, (g, _, _) in zip(rows, parcels):
        r["geometry_wkb"] = wkb.dumps(g.simplify(0.5, preserve_topology=True))
    prov.update(elevation=eprov, rows=len(rows), seconds_vector=round(t1 - t0, 1), seconds_elevation=round(time.time() - t1, 1))
    return rows, prov


REGION_CORE, REGION_NAMES = None, set()   # set by main for a region run


def plain(name):
    import unicodedata
    return unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().strip().lower()


def region_shapes(key):
    R = REGIONS[key]
    feats = arcgis.query_all(R["url"], dict(where=R["where"], outFields="NAME", outSR=2193))
    tas = [(ov.repaired(shape(f["geometry"])), f["properties"]) for f in feats if f.get("geometry")]
    region = unary_union([g for g, _ in tas])
    # grown only along the coast: the district polygons follow a simplified shore, so shore and island parcels fell
    # just outside; inland borders with other regions are left as they are (T-108)
    x0, y0, x1, y1 = region.bounds
    coast = arcgis.query_all(SVC + LAYERS["coast"][0] + "/FeatureServer/0", dict(where="1=1", geometry=f"{x0},{y0},{x1},{y1}",
        geometryType="esriGeometryEnvelope", inSR=2193, spatialRel="esriSpatialRelIntersects", outFields="id", outSR=2193), workers=WORKERS)
    shore = unary_union([shape(f["geometry"]) for f in coast if f.get("geometry")]).buffer(COAST_BAND)
    grown = region.union(region.buffer(REGION_MARGIN).intersection(shore))
    return grown, tas, dict(url=R["url"], features=len(feats), licence=R["licence"], fetched=utc_now(), name=R["name"],
                            grown=f"by up to {REGION_MARGIN:.0f} m within {COAST_BAND:.0f} m of the coast")


if __name__ == "__main__":
    out = sys.argv[1]; key = sys.argv[2] if len(sys.argv) > 2 else "wellington"
    os.makedirs(out, exist_ok=True); cache = os.path.join(out, "cache")
    t0 = time.time()
    region, tas, rprov = region_shapes(key)
    REGION_CORE = unary_union([g for g, _ in tas]); REGION_NAMES = {plain(p.get("NAME")) for _, p in tas}
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
