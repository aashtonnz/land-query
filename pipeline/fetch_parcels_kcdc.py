"""Fetch the block's primary parcels from KCDC's public Cadastral service (no key needed) and set the fetch window.

The layer mirrors LINZ NZ Primary Parcels (same fields: LINZ parcel id, appellation, titles, survey area), so parcel ids
join to LINZ (D-11). A parcel belongs to this block if its representative point lies inside the block. The fetch window is
the union of those parcels' bounds plus 30 m, capped at MAX_BUFFER beyond the block (tile_env.py). Run this first.
"""
import hashlib, json, os, sys, time
import requests
from shapely.geometry import shape, box
import tile_env as te

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
URL = "https://maps.kapiticoast.govt.nz/server/rest/services/Public/Cadastral/MapServer/0"
os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)

t0 = time.time(); feats = []; offset = 0
while True:
    p = dict(geometry=",".join(map(str, te.BLOCK)), geometryType="esriGeometryEnvelope", inSR=2193,
             spatialRel="esriSpatialRelIntersects", outFields="*", outSR=2193, f="geojson",
             resultOffset=offset, resultRecordCount=2000, orderByFields="OBJECTID")
    for attempt in range(4):
        try:
            r = requests.get(URL + "/query", params=p, timeout=300); r.raise_for_status(); break
        except requests.exceptions.RequestException:
            if attempt == 3: raise
            time.sleep(5 * (attempt + 1))
    batch = r.json().get("features", [])
    feats += batch; offset += len(batch)
    if len(batch) < 2000: break

blk = box(*te.BLOCK); kept = []
for f in feats:
    if not f.get("geometry"): continue
    g = shape(f["geometry"])
    if blk.contains(g.representative_point()) or blk.touches(g.representative_point()):
        kept.append(f)
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
prov.update(block=list(te.BLOCK), fetch_bbox=win)
prov["sources"]["parcels"] = dict(url=URL, ok=True, features=len(kept), sha256=hashlib.sha256(b).hexdigest(),
                                  seconds=round(time.time() - t0, 1), fetched=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                  licence="LINZ NZ Primary Parcels, CC BY 4.0, via KCDC public mirror (attribute LINZ)")
json.dump(prov, open(prov_path, "w"), indent=1)
print("parcels", len(kept), "of", len(feats), "intersecting; window", win, round(time.time() - t0, 1), "s")
