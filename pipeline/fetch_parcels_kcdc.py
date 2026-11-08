"""Choose the block's parcels and set the fetch window; parcel geometry from LINZ (T-51).

Candidate parcels come from KCDC's public Cadastral service, a mirror of LINZ NZ Primary Parcels (no key needed),
which is NOT clipped to the district; a parcel belongs to this block if the representative point of its mirror
polygon lies inside the block, and to the district under overlays.district_share (T-62, T-65). The mirror truncates some parcels lying inside the district (second review, T-49), so
each parcel's geometry and fields come from LINZ layer 50823 by parcel id when LINZ_API_KEY is set (GitHub runs).
A parcel LINZ does not return keeps the mirror polygon, marked in `geometry_source`. Without a key (a local session)
every parcel uses the mirror, and the provenance says so. The mirror is saved as raw/kcdc_parcels.geojson for QA.
The fetch window is the union of the parcels' bounds plus 30 m, capped at MAX_BUFFER beyond the block (tile_env.py).
Run this first.
"""
import hashlib, json, os, sys, time
from shapely.geometry import shape, box
import tile_env as te
import arcgis
import linz

from provenance import utc_now

from councils import COUNCIL as C   # the council's parcel copy and outline sources (T-86)

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
URL = C.PARCELS_URL
os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)

t0 = time.time()
feats = arcgis.query_all(URL, dict(geometry=",".join(map(str, te.BLOCK)), geometryType="esriGeometryEnvelope", inSR=2193,
                                   spatialRel="esriSpatialRelIntersects", outFields="*", outSR=2193))

# the district: the mirror holds hundreds of parcels in Porirua and Horowhenua (fourth review, T-62), so membership is
# tested here on every run, against three boundaries: KCDC's line and ward, and Stats NZ's polygon (T-65, T-70)
import overlays as ov
Q = lambda s: arcgis.query_all(s[0], dict(where=s[1], outFields=s[2], outSR=2193))
EDGE_URL, WARD_URL, STATS_URL = (C.OUTLINE[k][0] for k in ("line", "ward", "stats"))
edge, wards, stats = Q(C.OUTLINE["line"]), Q(C.OUTLINE["ward"]), Q(C.OUTLINE["stats"])
G = lambda fs: [ov.repaired(shape(f["geometry"])) for f in fs if f.get("geometry")]   # never buffer(0) (T-94)
district = (ov.district_outline_polygons(G(edge), G(wards), G(stats)) if C.OUTLINE.get("kind") == "polygons"
            else ov.district_outline(G(edge), G(wards), G(stats), sea_x=C.OUTLINE["sea_x"]))
if district.is_empty: raise SystemExit("could not build the district outline from the council's line and ward and Stats NZ's polygon")
outline_b = json.dumps(dict(type="FeatureCollection", features=edge + wards + stats), sort_keys=True).encode()
from shapely.geometry import mapping
json.dump(mapping(district), open(os.path.join(OUT, "raw", "district_outline.geojson"), "w"))  # for building cover (T-73)
mirror_ids = {f["properties"].get("id") for f in feats}

blk = box(*te.BLOCK); kept = []
# road and water parcels are not in LINZ's primary parcel layer (they have layers of their own), and KCDC's copy omits
# them; PCC's includes them, so they are left out here for every council (T-88)
for f in feats:
    if not f.get("geometry") or f["properties"].get("parcel_intent") in ov.NOT_PRIMARY_INTENTS: continue
    g = ov.repaired(shape(f["geometry"]))
    if blk.contains(g.representative_point()) or blk.touches(g.representative_point()):
        kept.append(f)
mirror = dict(type="FeatureCollection", features=kept)
open(os.path.join(OUT, "raw", C.PARCELS_KEY + ".geojson"), "w").write(json.dumps(mirror))
LINZ_URL = "https://data.linz.govt.nz/layer/50823/"
linz_err = None
if linz.KEY:
    try:
        by_id = {f["properties"].get("id"): f for f in linz.wfs(50823, te.BLOCK) if f.get("geometry")}
    except Exception as e:
        by_id, linz_err = {}, str(e)[:300]
else:
    by_id, linz_err = {}, "LINZ_API_KEY not set: mirror geometry used"
units = []
for f in kept:
    lf = by_id.get(f["properties"].get("id"))
    if lf is not None: lf["properties"]["geometry_source"] = "LINZ"; units.append(lf)
    else: f["properties"]["geometry_source"] = C.PARCELS_COPY; units.append(f)
kept = units
# LINZ parcels in this block (representative point inside it and inside the district) that the mirror lacks: new
# parcels, railway parcels, or the mirror lagging. Counted and listed for QA, not compiled (T-59).
missing = ov.linz_not_in_mirror(by_id, mirror_ids, blk, district) if by_id else []
# keep only the district's parcels, recording the share of each inside (T-62, T-65)
kept, outside = ov.split_by_district(kept, district)
from_linz = sum(1 for f in kept if f["properties"]["geometry_source"] == "LINZ")
fc = dict(type="FeatureCollection", features=kept)
b = json.dumps(fc).encode()
open(os.path.join(OUT, "raw", "parcels.geojson"), "wb").write(b)

if kept:
    bs = [shape(f["geometry"]).bounds for f in kept]
    u = (min(x[0] for x in bs) - 30, min(x[1] for x in bs) - 30, max(x[2] for x in bs) + 30, max(x[3] for x in bs) + 30)
    c = (te.BLOCK[0] - te.MAX_BUFFER, te.BLOCK[1] - te.MAX_BUFFER, te.BLOCK[2] + te.MAX_BUFFER, te.BLOCK[3] + te.MAX_BUFFER)
    win = [int(max(min(u[0], te.BLOCK[0]), c[0])), int(max(min(u[1], te.BLOCK[1]), c[1])),
           int(min(max(u[2], te.BLOCK[2]), c[2])) + 1, int(min(max(u[3], te.BLOCK[3]), c[3])) + 1]
else:
    win = list(te.BLOCK)
json.dump(dict(block=list(te.BLOCK), bbox=win, parcels=len(kept)), open(os.path.join(OUT, "fetch_bbox.json"), "w"))

prov_path = os.path.join(OUT, "provenance.json")
prov = json.load(open(prov_path)) if os.path.exists(prov_path) else {"sources": {}}
prov.update(block=list(te.BLOCK), block_id=te.BLOCK_ID, fetch_bbox=win)
prov.update(commit=os.environ.get("GITHUB_SHA"))  # the commit this block was compiled at (T-59)
linz_err = ov.parcels_error(bool(linz.KEY), kept, from_linz, linz_err)  # T-62
prov["sources"]["parcels"] = dict(url=LINZ_URL if from_linz else URL, ok=linz_err is None, features=len(kept),
                                  from_linz=from_linz, from_mirror=len(kept) - from_linz, linz_error=linz_err,
                                  linz_not_in_mirror=len(missing), linz_not_in_mirror_examples=missing[:20],
                                  outside_district=len(outside), outside_district_examples=outside[:20],
                                  membership=URL, sha256=hashlib.sha256(b).hexdigest(),
                                  seconds=round(time.time() - t0, 1), fetched=utc_now(),
                                  licence=f"LINZ NZ Primary Parcels, CC BY 4.0 (district membership from {C.PARCELS_FROM})")
mb = json.dumps(mirror).encode()
prov["sources"]["district_outline"] = dict(url=[EDGE_URL, WARD_URL, STATS_URL], ok=True, features=len(edge) + len(wards) + len(stats),
                                           area_km2=round(district.area / 1e6, 1), sha256=hashlib.sha256(outline_b).hexdigest(),
                                           fetched=utc_now(), licence=C.OUTLINE_LICENCE)
prov["sources"][C.PARCELS_KEY] = dict(url=URL, ok=True, features=len(mirror["features"]), sha256=hashlib.sha256(mb).hexdigest(),
                                       fetched=utc_now(), licence=f"LINZ NZ Primary Parcels, CC BY 4.0, via {C.PARCELS_VIA}")
json.dump(prov, open(prov_path, "w"), indent=1)
print("parcels", len(kept), "of", len(feats), "intersecting;", from_linz, "with LINZ geometry; window", win, round(time.time() - t0, 1), "s", linz_err or "")
