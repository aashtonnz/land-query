"""District plan zoning for the national index, from councils that publish it under an open licence (T-38).

The council survey (`council_survey.py`, docs/findings/2026-11-18-council-zoning-survey.md) lists the councils whose
zoning layer carries an open licence on the dataset. SOURCES below are those whose layer is current; each names the
plan it shows and its status. `fetch_all(OUT)` downloads them once (OUT/zoning.parquet: district, zone, wkb, bounds;
OUT/zoning.json: per source its address, plan, licence, fetch time and count), and `zone_columns` gives each parcel
the zone covering most of it, that zone's share of the parcel, a broad class, and the plan.

Usage: zoning.py OUT_DIR   (bulk.py calls fetch_all for the national build)
"""
import json, os, re, sys, time
import numpy as np, shapely
from shapely.geometry import shape
from shapely.strtree import STRtree

# district (as the national build names it in territorial_authority, without macrons), layer, zone field, plan and its status, licence as stated
SOURCES = [
    dict(district="Christchurch City", url="https://gis.ccc.govt.nz/server/rest/services/OpenData/DistrictPlan/FeatureServer/78",
         field="Type", where="RemovedByPlanChangeIdentifier IS NULL", plan="Christchurch District Plan", licence="CC BY 4.0 (Christchurch City Council Open Data)"),
    dict(district="Far North District", url="https://maps.fndc.govt.nz/hosting/rest/services/PDP_Decisions/PDPDecisions_Zones_FNDC/MapServer/0",
         field="zone", plan="Far North Proposed District Plan, decisions version (subject to appeal)", licence="CC BY 4.0"),
    dict(district="New Plymouth District", url="https://services2.arcgis.com/JthOmqz8HxPqljUO/arcgis/rest/services/OpenData_Strategy_DistrictPlan_PartOperative/FeatureServer/51",
         field="Zone", plan="New Plymouth District Plan, part operative", licence="CC BY 4.0"),
    dict(district="Hastings District", url="https://services1.arcgis.com/8L3DQUzjrkgEmDpQ/arcgis/rest/services/OpenData_OperativeDistrictPlan_Zones/FeatureServer/39",
         field="Zone", plan="Hastings District Plan, operative", licence="CC BY 4.0 (Hastings District Council)"),
    dict(district="Marlborough District", url="https://gis.marlborough.govt.nz/server/rest/services/OpenData/OpenData5/MapServer/18",
         field="ZoningCodeLabel", plan="Marlborough Environment Plan", licence="CC BY 4.0"),
    dict(district="Gisborne District", url="https://services7.arcgis.com/8G10QCd84QpdcTJ9/arcgis/rest/services/plan_zones/FeatureServer/0",
         field="ZONE", plan="Tairāwhiti Resource Management Plan", licence="CC BY 4.0 (Gisborne District Council)"),
    dict(district="Western Bay of Plenty District", url="https://map.westernbay.govt.nz/arcgisext/rest/services/District_Plan_WFS/MapServer/66",
         field="CS_PAR_ZONE", plan="Western Bay of Plenty District Plan", licence="CC BY 4.0"),
    dict(district="Taupo District", url="https://services7.arcgis.com/S7DHOirgbYgdtrbR/arcgis/rest/services/Zone_NPS_view/FeatureServer/0",
         field="Zone", where="Status='Operative'", plan="Taupō District Plan, operative zones", licence="CC BY 4.0"),
    dict(district="Manawatu District", url="https://services9.arcgis.com/CzWZ8m5FuciqBibe/arcgis/rest/services/District_Plan_Zones/FeatureServer/0",
         field="zone", plan="Manawatū District Plan", licence="CC BY 4.0"),
    dict(district="Tararua District", url="https://services-ap1.arcgis.com/ry1jWJjaLhqVCFK6/arcgis/rest/services/TRR_Planning/FeatureServer/0",
         field="Zoning", plan="Tararua District Plan", licence="CC BY 4.0 (Tararua District Council)"),
    dict(district="South Waikato District", url="https://services9.arcgis.com/pQ2VGNXWHZ4WkdmW/arcgis/rest/services/Plan_Zones/FeatureServer/1",
         field="ZONE_DESC", plan="South Waikato District Plan", licence="CC BY 4.0"),
]

# broad classes for comparing councils, first match wins; the council's own zone name is always published as well
CLASSES = [("special purpose", r"speci(fic|al) purpose|papak[aā]inga|m[aā]ori purpose|school|hospital|tertiary|education|golf|marina|major facilit"),
           ("open space", r"open space|reserve|recreation|park|conservation|natural|cemetery|sport|^os\d"),
           ("rural", r"rural|farm|horticult|production|forest"),
           ("industrial", r"industr"),
           ("business", r"business|commercial|centre|center|town|retail|mixed use|city centre|central area"),
           ("residential", r"residen|living|lifestyle|settlement|housing|urban"),
           ("infrastructure", r"road|rail|transport|airport|port|designat|^desig|infrastructure|utility|mineral extraction")]


def zone_class(name):
    t = (name or "").replace("_", " ").lower()
    for cls, pat in CLASSES:
        if re.search(pat, t): return cls
    return "other" if t.strip() else None


def fetch_all(out, sources=SOURCES):
    """Download every source to OUT/zoning.parquet and describe them in OUT/zoning.json. A source that cannot be read
    is recorded as failed and left out: its district's parcels lack zoning that month, which the monthly comparison
    sees as more empty values and holds for a person (D-27). Fails only if none can be read."""
    import arcgis, pyarrow as pa, pyarrow.parquet as pq
    from provenance import utc_now
    rows = dict(district=[], zone=[], wkb=[], xmin=[], ymin=[], xmax=[], ymax=[]); meta = {}
    for s in sources:
        t0 = time.time()
        try: feats = arcgis.query_all(s["url"], dict(where=s.get("where", "1=1"), outFields=s["field"], outSR=2193), workers=2)
        except Exception as e:
            meta[s["district"]] = dict(url=s["url"], plan=s["plan"], failed=str(e)[:300], fetched=utc_now())
            print(s["district"], "FAILED:", str(e)[:200], flush=True); continue
        n = 0
        for f in feats:
            name = ((f.get("properties") or {}).get(s["field"]) or "").strip()
            if not f.get("geometry") or not name: continue
            g = shapely.make_valid(shape(f["geometry"]))
            if g.is_empty: continue
            b = g.bounds
            rows["district"].append(s["district"]); rows["zone"].append(name); rows["wkb"].append(shapely.to_wkb(g))
            for k, v in zip(("xmin", "ymin", "xmax", "ymax"), b): rows[k].append(v)
            n += 1
        if n == 0:
            meta[s["district"]] = dict(url=s["url"], plan=s["plan"], failed="no zones read", fetched=utc_now()); continue
        meta[s["district"]] = dict(url=s["url"], plan=s["plan"], licence=s["licence"], field=s["field"], where=s.get("where"),
                                   fetched=utc_now(), features=n, seconds=round(time.time() - t0))
        print(s["district"], meta[s["district"]], flush=True)
    if not rows["zone"]: raise RuntimeError("no council zoning could be read")
    os.makedirs(out, exist_ok=True)
    pq.write_table(pa.table(dict(rows, wkb=pa.array(rows["wkb"], pa.binary()))), os.path.join(out, "zoning.parquet"), compression="zstd")
    json.dump(meta, open(os.path.join(out, "zoning.json"), "w"), indent=1)
    return meta


def load(path, bbox=None):
    """[(geometry, district, zone)] from zoning.parquet, within bbox if given."""
    import pyarrow.dataset as ds
    d = ds.dataset(path)
    f = None
    if bbox:
        x0, y0, x1, y1 = bbox
        f = (ds.field("xmin") <= x1) & (ds.field("xmax") >= x0) & (ds.field("ymin") <= y1) & (ds.field("ymax") >= y0)
    t = d.to_table(filter=f)
    gs = shapely.from_wkb(t.column("wkb").to_numpy(zero_copy_only=False))
    return list(zip(gs, t.column("district").to_pylist(), t.column("zone").to_pylist()))


def zone_columns(parcels, zones, meta, overlap):
    """Per parcel: dict(zone, zone_share_pct, zone_class, zone_plan). The zone covering most of the parcel; empty where
    no published zoning reaches it (a council not yet covered, or a parcel outside the zoned area)."""
    tree = STRtree([g for g, _, _ in zones]) if zones else None
    out = []
    for g, _, _ in parcels:
        best, area = None, 0.0
        if tree is not None and g.area > 0:
            by = {}
            for i in tree.query(g):
                zg, d, z = zones[int(i)]
                a = overlap(g, zg).area
                if a > 0: by[(d, z)] = by.get((d, z), 0.0) + a
            if by: best, area = max(by.items(), key=lambda kv: kv[1])
        if best is None:
            out.append(dict(zone=None, zone_share_pct=None, zone_class=None, zone_plan=None)); continue
        d, z = best
        out.append(dict(zone=z, zone_share_pct=round(min(100.0, 100.0 * area / g.area), 1), zone_class=zone_class(z),
                        zone_plan=meta.get(d, {}).get("plan")))
    return out


if __name__ == "__main__":
    fetch_all(sys.argv[1])
