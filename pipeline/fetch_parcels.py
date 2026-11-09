"""Fetch LINZ titles and non-primary parcels (incl. easements) for the fetch window via LDS WFS (needs LINZ_API_KEY; CC BY 4.0)."""
import hashlib, json, os, sys, time
from provenance import utc_now
import tile_env as te
import linz

KEY = os.environ.get("LINZ_API_KEY")
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
TILE = te.fetch_bbox(OUT)  # fetch window (block grown to cover its parcels)
from councils import COUNCIL as C
if not KEY and getattr(C, "TITLES_URL", None):
    # without the key (the national report run locally, T-101): titles from LINZ's public ArcGIS copy, live titles'
    # number and type only; easements have no public copy, so they are recorded as not fetched
    import arcgis
    t0 = time.time(); prov_path = os.path.join(OUT, "provenance.json"); prov = json.load(open(prov_path))
    fs = arcgis.query_all(C.TITLES_URL, dict(where="status IN ('LIVE','PRTC')", geometry=",".join(map(str, TILE)), geometryType="esriGeometryEnvelope",
                                             inSR=2193, spatialRel="esriSpatialRelIntersects", outFields="title_no,status,type", outSR=2193), workers=4)
    b = json.dumps(dict(type="FeatureCollection", features=fs)).encode()
    open(os.path.join(OUT, "raw", "titles.geojson"), "wb").write(b)
    prov["sources"]["titles"] = dict(url=C.TITLES_URL, same_as="https://data.linz.govt.nz/layer/50804/", ok=True, features=len(fs),
                                     sha256=hashlib.sha256(b).hexdigest(), seconds=round(time.time() - t0, 1),
                                     fetched=utc_now(), licence="LINZ CC BY 4.0")
    prov["sources"]["nonprimary_parcels"] = dict(url="https://data.linz.govt.nz/layer/50782/", ok=False,
                                                 error="not fetched: LINZ_API_KEY not set and no public copy")
    json.dump(prov, open(prov_path, "w"), indent=1); print("titles", len(fs), "(LINZ ArcGIS); easements not fetched")
    sys.exit(0)
if not KEY: sys.exit("LINZ_API_KEY not set")
LAYERS = {"titles": 50804, "nonprimary_parcels": 50782}  # primary parcels: fetch_parcels_kcdc.py (T-51)

prov_path = os.path.join(OUT, "provenance.json"); prov = json.load(open(prov_path))
for name, lid in LAYERS.items():
    t0 = time.time()
    try:
        fc = dict(type="FeatureCollection", features=linz.wfs(lid, TILE)); b = json.dumps(fc).encode()
        open(os.path.join(OUT, "raw", name + ".geojson"), "wb").write(b)
        prov["sources"][name] = dict(url=f"https://data.linz.govt.nz/layer/{lid}/", ok=True, features=len(fc["features"]),
                                     sha256=hashlib.sha256(b).hexdigest(), seconds=round(time.time() - t0, 1),
                                     fetched=utc_now(), licence="LINZ CC BY 4.0")
        print(name, len(fc["features"]), round(time.time() - t0, 1), "s")
    except Exception as e:
        prov["sources"][name] = dict(ok=False, error=str(e).replace(KEY, "***")[:300]); print(name, "FAILED")
json.dump(prov, open(prov_path, "w"), indent=1)
