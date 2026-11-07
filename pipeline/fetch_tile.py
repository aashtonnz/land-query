"""Fetch the block's fetch window from public KCDC and GWRC layers, logging provenance.

Every fetched source is written to data/raw/ and recorded in data/provenance.json with
URL, fetch time, sha256, feature count and licence note. Nothing is invented: a source
that fails is recorded as failed.
"""
import hashlib, json, os, sys, time
from provenance import utc_now

import tile_env as te
import arcgis

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
_W = te.fetch_bbox(OUT)  # block grown to cover its parcels (fetch_parcels_kcdc.py)
TILE = dict(xmin=_W[0], ymin=_W[1], xmax=_W[2], ymax=_W[3])  # NZTM2000 (EPSG:2193)
RAW = os.path.join(OUT, "raw"); os.makedirs(RAW, exist_ok=True)
from layers import KC, KC_LIC, ARCGIS  # noqa: F401  (the layer list, shared with source_check.py)

def sha(b): return hashlib.sha256(b).hexdigest()

WHOLE = {"district_boundary"}  # small layers fetched whole: a large parcel can cross the boundary outside the window


def arcgis_query(url, whole=False):
    """Every feature of an ArcGIS layer intersecting the fetch window (or all of it), as GeoJSON in EPSG:2193."""
    env = f"{TILE['xmin']},{TILE['ymin']},{TILE['xmax']},{TILE['ymax']}"
    q = dict(where="1=1", outFields="*", outSR=2193, returnGeometry="true")
    if not whole: q.update(geometry=env, geometryType="esriGeometryEnvelope", inSR=2193, spatialRel="esriSpatialRelIntersects")
    return {"type": "FeatureCollection", "features": arcgis.query_all(url, q)}

def main():
    pp = os.path.join(OUT, "provenance.json")
    prov = json.load(open(pp)) if os.path.exists(pp) else {"sources": {}}
    prov.update(tile_nztm=TILE, block_id=te.BLOCK_ID, fetched_at=utc_now())
    only = set(os.environ.get("ONLY", "").split(",")) - {""}
    for name, (url, lic) in ARCGIS.items():
        if only and name not in only: continue
        t0 = time.time()
        try:
            fc = arcgis_query(url, whole=name in WHOLE)
            b = json.dumps(fc).encode()
            open(os.path.join(RAW, name + ".geojson"), "wb").write(b)
            meta = arcgis._get(url, {"f": "json"}, 60)
            prov["sources"][name] = dict(url=url, ok=True, features=len(fc["features"]), bytes=len(b), sha256=sha(b),
                                         seconds=round(time.time() - t0, 2), fetched=utc_now(), licence=lic,
                                         layer_name=meta.get("name"), copyright=te.scrub_copyright(meta.get("copyrightText")))
            print(f"{name:26s} {len(fc['features']):6d} features  {time.time()-t0:5.1f}s")
        except Exception as e:
            prov["sources"][name] = dict(url=url, ok=False, error=str(e)[:300], licence=lic)
            print(f"{name:26s} FAILED {e}")
    json.dump(prov, open(os.path.join(OUT, "provenance.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
