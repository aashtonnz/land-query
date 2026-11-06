"""Fetch primary parcels for the tile from KCDC's public Cadastral service (no key needed).

The layer mirrors LINZ NZ Primary Parcels (same fields: LINZ parcel id, appellation, titles, survey area),
so parcel ids join to LINZ. Mirror refresh date is not published; see the findings for the cross-check.
Writes data/raw/parcels.geojson, which compile_tile.py then uses as its unit. Run after fetch_tile.py.
"""
import hashlib, json, os, sys, time
import requests

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
TILE = (1769000, 5468400, 1770000, 5469400)
URL = "https://maps.kapiticoast.govt.nz/server/rest/services/Public/Cadastral/MapServer/0"

t0 = time.time(); feats = []; offset = 0
while True:
    p = dict(geometry=",".join(map(str, TILE)), geometryType="esriGeometryEnvelope", inSR=2193,
             spatialRel="esriSpatialRelIntersects", outFields="*", outSR=2193, f="geojson",
             resultOffset=offset, resultRecordCount=1000, orderByFields="OBJECTID")
    r = requests.get(URL + "/query", params=p, timeout=300); r.raise_for_status()
    fc = r.json(); batch = fc.get("features", [])
    feats += batch; offset += len(batch)
    if len(batch) < 1000: break
fc = dict(type="FeatureCollection", features=feats)
b = json.dumps(fc).encode()
os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)
open(os.path.join(OUT, "raw", "parcels.geojson"), "wb").write(b)
prov_path = os.path.join(OUT, "provenance.json")
prov = json.load(open(prov_path)) if os.path.exists(prov_path) else {"sources": {}}
prov["sources"]["parcels"] = dict(url=URL, ok=True, features=len(feats), sha256=hashlib.sha256(b).hexdigest(),
                                  seconds=round(time.time() - t0, 1), fetched=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                                  licence="LINZ NZ Primary Parcels, CC BY 4.0, via KCDC public mirror (attribute LINZ)")
json.dump(prov, open(prov_path, "w"), indent=1)
print("parcels", len(feats), round(time.time() - t0, 1), "s")
