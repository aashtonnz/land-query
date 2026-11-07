"""LINZ Data Service WFS (needs LINZ_API_KEY, held only as a GitHub repository secret; CC BY 4.0)."""
import os, time
import requests

KEY = os.environ.get("LINZ_API_KEY")


def wfs(layer, bbox):
    """Every feature of LINZ layer `layer` intersecting bbox (xmin, ymin, xmax, ymax, NZTM2000), as GeoJSON features."""
    if not KEY: raise RuntimeError("LINZ_API_KEY not set")
    b = f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]},urn:ogc:def:crs:EPSG::2193"  # WFS 2.0: northing, easting
    url = f"https://data.linz.govt.nz/services;key={KEY}/wfs"
    feats, start, page = [], 0, 10000
    while True:  # page with startIndex so large windows are complete
        p = dict(service="WFS", version="2.0.0", request="GetFeature", typeNames=f"layer-{layer}",
                 srsName="EPSG:2193", bbox=b, outputFormat="application/json", count=page, startIndex=start, sortBy="id")
        for attempt in range(4):
            try:
                r = requests.get(url, params=p, timeout=300); r.raise_for_status(); break
            except requests.exceptions.RequestException as e:
                if attempt == 3: raise RuntimeError(str(e).replace(KEY, "***")) from None
                time.sleep(5 * (attempt + 1))
        batch = r.json().get("features", [])
        feats += batch; start += len(batch)
        if len(batch) < page: return feats
