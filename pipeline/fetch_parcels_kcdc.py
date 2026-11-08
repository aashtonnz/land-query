"""Choose the block's parcels and set the fetch window; parcel geometry from LINZ (T-51).

Which parcels belong to the district comes from KCDC's public Cadastral service, a mirror of LINZ NZ Primary Parcels
clipped to the district (no key needed); a parcel belongs to this block if the representative point of its mirror
polygon lies inside the block. The mirror truncates some parcels lying inside the district (second review, T-49), so
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

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
URL = "https://maps.kapiticoast.govt.nz/server/rest/services/Public/Cadastral/MapServer/0"
os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)

t0 = time.time()
feats = arcgis.query_all(URL, dict(geometry=",".join(map(str, te.BLOCK)), geometryType="esriGeometryEnvelope", inSR=2193,
                                   spatialRel="esriSpatialRelIntersects", outFields="*", outSR=2193))

# the district, from KCDC's boundary line closed at sea: the mirror is NOT clipped to it, and holds hundreds of parcels in
# Porirua and Horowhenua (fourth review, T-62), so membership is tested here on every run
from overlays import district_polygon
edge = arcgis.query_all(URL.rsplit("/", 1)[0] + "/1", dict(where="1=1", outFields="OBJECTID", outSR=2193))
district = district_polygon([shape(f["geometry"]) for f in edge if f.get("geometry")])
if district.is_empty: raise SystemExit("could not build the district outline from KCDC's boundary line")
mirror_ids = {f["properties"].get("id") for f in feats}

blk = box(*te.BLOCK); kept = []
for f in feats:
    if not f.get("geometry"): continue
    g = shape(f["geometry"])
    if blk.contains(g.representative_point()) or blk.touches(g.representative_point()):
        kept.append(f)
mirror = dict(type="FeatureCollection", features=kept)
open(os.path.join(OUT, "raw", "kcdc_parcels.geojson"), "w").write(json.dumps(mirror))
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
    else: f["properties"]["geometry_source"] = "KCDC mirror"; units.append(f)
kept = units
# LINZ parcels in this block (representative point inside it and inside the district) that the mirror lacks: new
# parcels, railway parcels, or the mirror lagging. Counted and listed for QA, not compiled (T-59).
missing = []
if by_id:
    for i, f in by_id.items():
        if i in mirror_ids: continue  # in the mirror, whichever block it was assigned to (T-62)
        p = shape(f["geometry"]).representative_point()
        if (blk.contains(p) or blk.touches(p)) and district.contains(p):
            missing.append(dict(id=i, appellation=f["properties"].get("appellation"), intent=f["properties"].get("parcel_intent")))
# keep a parcel only if its representative point lies in the district; record the share of it inside (T-62)
inside, outside = [], []
for f in kept:
    g = shape(f["geometry"])
    if district.contains(g.representative_point()):
        f["properties"]["district_share_pct"] = round(100 * g.intersection(district).area / g.area, 1) if g.area else None
        inside.append(f)
    else:
        outside.append(dict(id=f["properties"].get("id"), appellation=f["properties"].get("appellation")))
kept = inside
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
if linz.KEY and kept and not from_linz and not linz_err: linz_err = "LINZ returned none of the block's parcels"  # T-62
prov["sources"]["parcels"] = dict(url=LINZ_URL if from_linz else URL, ok=linz_err is None, features=len(kept),
                                  from_linz=from_linz, from_mirror=len(kept) - from_linz, linz_error=linz_err,
                                  linz_not_in_mirror=len(missing), linz_not_in_mirror_examples=missing[:20],
                                  outside_district=len(outside), outside_district_examples=outside[:20],
                                  membership=URL, sha256=hashlib.sha256(b).hexdigest(),
                                  seconds=round(time.time() - t0, 1), fetched=utc_now(),
                                  licence="LINZ NZ Primary Parcels, CC BY 4.0 (district membership from KCDC's public mirror)")
mb = json.dumps(mirror).encode()
prov["sources"]["kcdc_parcels"] = dict(url=URL, ok=True, features=len(mirror["features"]), sha256=hashlib.sha256(mb).hexdigest(),
                                       fetched=utc_now(), licence="LINZ NZ Primary Parcels, CC BY 4.0, via KCDC public mirror")
json.dump(prov, open(prov_path, "w"), indent=1)
print("parcels", len(kept), "of", len(feats), "intersecting;", from_linz, "with LINZ geometry; window", win, round(time.time() - t0, 1), "s", linz_err or "")
