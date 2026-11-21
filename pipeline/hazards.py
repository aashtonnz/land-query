"""Flood and coastal hazard areas for the national index, from councils that map them under an open licence (T-128).

A council's hazard maps differ from another's (return periods, climate scenarios, modelled or mapped), so each source
below names exactly what its area is, and the index publishes, per parcel and kind (flood, coastal):
- `{kind}_area_pct`: the share of the parcel inside the area the council maps, 0 where the council maps it and the
  parcel lies outside; empty where the council publishes no such map openly (most of the country for now);
- `{kind}_area`: what that area is, in the council's terms (for example "Taupō District Plan: Flood Hazard Area, 1%
  annual exceedance probability").
Only areas a council uses now (its district plan or current hazard maps) are used, never future-scenario layers alone.

`fetch_all(OUT)` downloads them once (OUT/hazards.parquet, OUT/hazards.json); `hazard_columns` gives the columns.
Usage: hazards.py OUT_DIR   (bulk.py calls fetch_all for the national build)
"""
import json, os, sys, time
import shapely
from shapely.geometry import shape
from shapely.strtree import STRtree

KINDS = ("flood", "coastal")
FNDC = "https://services5.arcgis.com/H4FlrMy6xTBd6Ywx/arcgis/rest/services/"
SOURCES = [
    # flood
    dict(district="Christchurch City", kind="flood", label="Christchurch District Plan: Flood Management Area",
         urls=["https://gis.ccc.govt.nz/server/rest/services/OpenData/DistrictPlanB/FeatureServer/30"],
         where="RemovedByPlanChangeIdentifier IS NULL", licence="CC BY 4.0 (Christchurch City Council Open Data)"),
    dict(district="Taupo District", kind="flood", label="Taupō District Plan: Flood Hazard Area, 1% annual exceedance probability",
         urls=["https://services7.arcgis.com/S7DHOirgbYgdtrbR/arcgis/rest/services/Flood_Hazard_Area_1_percent_AEP_NPS_view/FeatureServer/0"],
         licence="CC BY 4.0"),
    dict(district="Gisborne District", kind="flood", label="Tairāwhiti Resource Management Plan: flood hazard areas (F1 to F9)",
         urls=["https://services7.arcgis.com/8G10QCd84QpdcTJ9/arcgis/rest/services/plan_flood_hazard/FeatureServer/0"],
         licence="CC BY 4.0 (Gisborne District Council)"),
    dict(district="Waipa District", kind="flood", label="Waipā District Plan: Special Feature Area, Flood Hazard",
         urls=["https://services9.arcgis.com/OsxSXqmTWVTZQ9ie/arcgis/rest/services/WaipaDistrictPlan_SpecialFeature_Area_Flood/FeatureServer/0"],
         licence="CC BY 4.0"),
    dict(district="Far North District", kind="flood", label="Far North Proposed District Plan: River Flood Hazard Zone, 100 year event",
         urls=[FNDC + "PDP_HazardsRivers_OpenData_FNDC/FeatureServer/1"], licence="CC BY 4.0"),
    # coastal
    dict(district="Gisborne District", kind="coastal", label="Tairāwhiti Resource Management Plan: Coastal Hazard Overlay (CH1 extreme to CH4 safety buffer)",
         urls=["https://services7.arcgis.com/8G10QCd84QpdcTJ9/arcgis/rest/services/plan_coastal_hazard/FeatureServer/0"],
         licence="CC BY 4.0 (Gisborne District Council)"),
    dict(district="Far North District", kind="coastal",
         label="Far North Proposed District Plan, decisions version: coastal flood and coastal erosion zones (50 year, 100 year and 100 year with rapid sea level rise)",
         urls=[FNDC + f"PDPDecisions_Hazards_Coastal{k}_FNDC_opendata/FeatureServer/{i}" for k in ("Flood", "Erosion") for i in range(3)],
         licence="CC BY 4.0"),
    dict(district="Nelson City", kind="coastal", label="Nelson coastal flooding, present day (2020), Tonkin & Taylor for Nelson City Council",
         urls=["https://services1.arcgis.com/Y4k7lyf2XTGeQC6V/arcgis/rest/services/Present_Day/FeatureServer/5"], licence="CC BY 4.0"),
]
# Not used, and why (Nov 2026): Christchurch's coastal layers hold future scenarios only (2065 to 2130); Hawke's Bay's
# coastal erosion is by probability and year to 2120; regional fault and liquefaction studies differ in kind from plan
# areas and wait for their own columns; Auckland's and Wellington City's licences wait for the councils (T-35).


def polygonal(geom):
    """The polygon part of a repaired shape, or None: repair can leave lines or points beside the polygons, and a merge of
    mixed kinds fails. One of Far North's flood zones (24,502 pieces, some too short to be polygons) defeats even the
    default repair ("Overlay input is mixed-dimension"); the structure method repairs it."""
    try: g = shapely.make_valid(geom)
    except shapely.errors.GEOSException: g = shapely.make_valid(geom, method="structure", keep_collapsed=False)
    polys = [p for p in shapely.get_parts(g) if p.geom_type in ("Polygon", "MultiPolygon")]
    while any(p.geom_type == "GeometryCollection" for p in shapely.get_parts(g)) and not polys:
        g = shapely.union_all([q for p in shapely.get_parts(g) for q in shapely.get_parts(p)]); polys = [p for p in shapely.get_parts(g) if p.geom_type in ("Polygon", "MultiPolygon")]
    if not polys: return None
    out = shapely.union_all(polys)
    return None if out.is_empty else out


def fetch_all(out, sources=SOURCES):
    """Download every source to OUT/hazards.parquet and describe them in OUT/hazards.json. A source that cannot be
    read is recorded as failed and left out (its district's values are then empty, never 0)."""
    import arcgis, pyarrow as pa, pyarrow.parquet as pq
    from provenance import utc_now
    rows = dict(district=[], kind=[], wkb=[], xmin=[], ymin=[], xmax=[], ymax=[]); meta = {}
    for s in sources:
        key = f'{s["district"]}|{s["kind"]}'; t0 = time.time(); n = 0
        try:
            for u in s["urls"]:
                # all fields (some layers' id field is not OBJECTID), simplified to 1 m (hazard areas are mapped far more
                # coarsely; Christchurch's came at 0.7 MB a polygon), 100 at a time
                for f in arcgis.query_all(u, dict(where=s.get("where", "1=1"), outFields="*", outSR=2193, maxAllowableOffset=1), workers=4, page_size=100):
                    if not f.get("geometry"): continue
                    g = polygonal(shape(f["geometry"]))
                    if g is None: continue
                    rows["district"].append(s["district"]); rows["kind"].append(s["kind"]); rows["wkb"].append(shapely.to_wkb(g))
                    for k, v in zip(("xmin", "ymin", "xmax", "ymax"), g.bounds): rows[k].append(v)
                    n += 1
        except Exception as e:
            meta[key] = dict(district=s["district"], kind=s["kind"], label=s["label"], urls=s["urls"], failed=str(e)[:300], fetched=utc_now())
            print(key, "FAILED:", str(e)[:200], flush=True); continue
        meta[key] = dict(district=s["district"], kind=s["kind"], label=s["label"], urls=s["urls"], where=s.get("where"), licence=s["licence"],
                         fetched=utc_now(), features=n, seconds=round(time.time() - t0), **({} if n else dict(failed="no areas read")))
        print(key, n, "areas", flush=True)
    if not rows["kind"]: raise RuntimeError("no council hazard areas could be read")
    os.makedirs(out, exist_ok=True)
    pq.write_table(pa.table(dict(rows, wkb=pa.array(rows["wkb"], pa.binary()))), os.path.join(out, "hazards.parquet"), compression="zstd")
    json.dump(meta, open(os.path.join(out, "hazards.json"), "w"), indent=1)
    return meta


def load(path, bbox=None):
    """[(geometry, district, kind)] from hazards.parquet, within bbox if given."""
    import pyarrow.dataset as ds
    f = None
    if bbox:
        x0, y0, x1, y1 = bbox
        f = (ds.field("xmin") <= x1) & (ds.field("xmax") >= x0) & (ds.field("ymin") <= y1) & (ds.field("ymax") >= y0)
    t = ds.dataset(path).to_table(filter=f)
    gs = shapely.from_wkb(t.column("wkb").to_numpy(zero_copy_only=False))
    return list(zip(gs, t.column("district").to_pylist(), t.column("kind").to_pylist()))


def hazard_columns(parcels, areas, meta, overlap, districts):
    """Per parcel: {kind}_area_pct and {kind}_area for each kind. Only the parcel's own council's areas count; pieces
    are merged so overlapping areas count once. Empty where its council maps no such area openly (or the map failed)."""
    tree = STRtree([g for g, _, _ in areas]) if areas else None
    mapped = {(m["district"], m["kind"]): m["label"] for m in meta.values() if not m.get("failed")}
    out = []
    for (g, _, _), own in zip(parcels, districts):
        r = {}
        for kind in KINDS:
            label = mapped.get((own, kind))
            if label is None: r[f"{kind}_area_pct"] = r[f"{kind}_area"] = None; continue
            pieces = []
            if tree is not None and g.area > 0:
                for i in tree.query(g):
                    ag, d, k = areas[int(i)]
                    if d == own and k == kind:
                        p = overlap(g, ag)
                        if p.area > 0: pieces.append(p)
            a = (shapely.union_all(pieces).area if len(pieces) > 1 else pieces[0].area) if pieces else 0.0
            r[f"{kind}_area_pct"] = round(min(100.0, 100.0 * a / g.area), 1) if g.area > 0 else None
            r[f"{kind}_area"] = label
        out.append(r)
    return out


if __name__ == "__main__":
    fetch_all(sys.argv[1])
