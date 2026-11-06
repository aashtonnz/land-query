"""Paging through ArcGIS REST layers, with a check that every feature arrived (T-44)."""
import time
import requests


def _get(url, params, timeout=300):
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=timeout); r.raise_for_status()
            j = r.json()
            if "error" in j: raise RuntimeError(j["error"])
            return j
        except (requests.exceptions.RequestException, ValueError):
            if attempt == 3: raise
            time.sleep(5 * (attempt + 1))


def exceeded(j):
    """ArcGIS puts exceededTransferLimit at the top level in f=json, and under properties in f=geojson."""
    return bool(j.get("exceededTransferLimit") or (j.get("properties") or {}).get("exceededTransferLimit"))


def page_through(fetch_page, page):
    """Collect pages from fetch_page(offset, page) until a short page that is not marked as truncated."""
    feats, offset = [], 0
    while True:
        j = fetch_page(offset, page)
        fs = j.get("features", [])
        feats += fs; offset += len(fs)
        if not fs or (len(fs) < page and not exceeded(j)): return feats


def query_all(url, query):
    """Every feature matching query (ArcGIS query parameters), as GeoJSON features in the requested outSR.

    Pages at the layer's own maxRecordCount, then checks the total against returnCountOnly and fails if any are
    missing, so a layer can never be silently cut short."""
    try: page = int(_get(url, {"f": "json"}, 60).get("maxRecordCount") or 1000)
    except Exception: page = 1000
    page = max(1, min(page, 5000))
    base = dict(query, f="geojson", orderByFields=query.get("orderByFields", "OBJECTID"))
    feats = page_through(lambda o, n: _get(url + "/query", dict(base, resultOffset=o, resultRecordCount=n)), page)
    n = _get(url + "/query", dict({k: v for k, v in query.items() if k not in ("outFields", "outSR")},
                                  returnCountOnly="true", f="json")).get("count")
    if n is not None and n != len(feats):
        raise RuntimeError(f"incomplete download: {len(feats)} features of {n}")
    return feats
