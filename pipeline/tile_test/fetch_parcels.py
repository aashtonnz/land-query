"""Fetch LINZ parcels, titles and easements for the tile via LDS WFS (needs LINZ_API_KEY; CC BY 4.0 layers)."""
import hashlib, json, os, sys, time
import requests

KEY = os.environ.get("LINZ_API_KEY")
if not KEY: sys.exit("LINZ_API_KEY not set")
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
TILE = (1769000, 5468400, 1770000, 5469400)
LAYERS = {"parcels": 50823, "titles": 50804, "nonprimary_parcels": 50782}

def wfs(layer):
    # EPSG:2193 axis order is northing, easting for WFS 2.0
    bbox = f"{TILE[1]},{TILE[0]},{TILE[3]},{TILE[2]},urn:ogc:def:crs:EPSG::2193"
    url = f"https://data.linz.govt.nz/services;key={KEY}/wfs"
    p = dict(service="WFS", version="2.0.0", request="GetFeature", typeNames=f"layer-{layer}",
             srsName="EPSG:2193", bbox=bbox, outputFormat="application/json", count=20000)
    r = requests.get(url, params=p, timeout=300); r.raise_for_status()
    return r.json()

prov_path = os.path.join(OUT, "provenance.json"); prov = json.load(open(prov_path))
for name, lid in LAYERS.items():
    t0 = time.time()
    try:
        fc = wfs(lid); b = json.dumps(fc).encode()
        open(os.path.join(OUT, "raw", name + ".geojson"), "wb").write(b)
        prov["sources"][name] = dict(url=f"https://data.linz.govt.nz/layer/{lid}/", ok=True, features=len(fc["features"]),
                                     sha256=hashlib.sha256(b).hexdigest(), seconds=round(time.time() - t0, 1),
                                     licence="LINZ CC BY 4.0")
        print(name, len(fc["features"]), round(time.time() - t0, 1), "s")
    except Exception as e:
        prov["sources"][name] = dict(ok=False, error=str(e).replace(KEY, "***")[:300]); print(name, "FAILED")
json.dump(prov, open(prov_path, "w"), indent=1)
