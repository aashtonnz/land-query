"""Paging through ArcGIS REST layers, with a check that every feature arrived (T-44)."""
import time
import requests


RATE_LIMIT_WAITS = (65, 120, 240, 480, 600, 600)   # seconds; the limit may be shared with other users of LINZ's service


def _get(url, params, timeout=300, post=False):
    limited = 0
    for attempt in range(4 + len(RATE_LIMIT_WAITS)):
        try:
            r = (requests.post(url, data=params, timeout=timeout) if post else requests.get(url, params=params, timeout=timeout))
            if r.status_code == 429: raise _RateLimited(r.headers.get("Retry-After"))
            if r.status_code >= 500: raise _RateLimited(None)   # a busy service: the same long waits (T-119)
            r.raise_for_status()
            j = r.json()
            if "error" in j:
                if (j["error"] or {}).get("code") == 429: raise _RateLimited()
                raise RuntimeError(j["error"])
            return j
        except _RateLimited as e:
            # a rate limit or busy service is waited out with longer and longer pauses, or as long as the service asks
            # (Retry-After), up to about 35 minutes in all (T-115, T-117, T-119)
            if limited >= len(RATE_LIMIT_WAITS): raise RuntimeError("rate limited or busy: gave up after waiting about 35 minutes")
            ask = e.args[0] if e.args else None
            time.sleep(max(RATE_LIMIT_WAITS[limited], float(ask)) if ask and str(ask).isdigit() else RATE_LIMIT_WAITS[limited]); limited += 1
        except (requests.exceptions.RequestException, ValueError):
            if attempt - limited >= 3: raise
            time.sleep(5 * (attempt - limited + 1))


class _RateLimited(Exception): pass


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


def _with_field(out_fields, oid):
    """outFields plus the object id field, and whether it was added (so it can be dropped again)."""
    fields = [f.strip() for f in (out_fields or "*").split(",")]
    if "*" in fields or oid in fields: return ",".join(fields), False
    return ",".join(fields + [oid]), True


def check_chunk(feats, want, oid):
    """Fail unless the features are exactly the requested object ids, once each (T-100: a service returned another
    page's features in place of the last page, which a count check cannot see)."""
    got = [(f.get("properties") or {}).get(oid, f.get("id")) for f in feats]
    if len(got) != len(set(got)) or set(got) != set(want):
        raise RuntimeError(f"features returned are not the {len(want)} requested: {len(got)} returned, "
                           f"{len(set(want) - set(got))} missing, {len(got) - len(set(got))} repeated")


SELECT_KEYS = frozenset({"where", "geometry", "geometryType", "inSR", "spatialRel", "text", "time", "distance", "units"})


def query_all(url, query, workers=1):
    """Every feature matching query (ArcGIS query parameters), as GeoJSON features in the requested outSR.

    Asks for the matching object ids first, then fetches them in chunks and checks that each chunk holds exactly the
    ids asked for, so a layer is never silently cut short or padded with repeats (T-100). A layer that cannot list its
    ids is paged by offset instead, with the total checked against returnCountOnly and repeats refused (T-44).
    With workers > 1 the chunks are fetched in parallel."""
    try: info = _get(url, {"f": "json"}, 60)
    except Exception: info = {}
    page = max(1, min(int(info.get("maxRecordCount") or 1000), 2000))
    oid = info.get("objectIdField") or next((f["name"] for f in info.get("fields") or [] if f.get("type") == "esriFieldTypeOID"), "OBJECTID")
    sel = {k: v for k, v in query.items() if k in SELECT_KEYS}
    try:
        r = _get(url + "/query", dict(sel, returnIdsOnly="true", f="json"), post=True)
        ids = None if exceeded(r) else sorted(r.get("objectIds") or [])
        oid = r.get("objectIdFieldName") or oid
    except Exception:
        ids = None
    fields, added = _with_field(query.get("outFields"), oid)
    base = dict(query, outFields=fields, f="geojson")
    if ids is not None:
        def chunk(c):
            fs = _get(url + "/query", dict({k: v for k, v in base.items() if k not in SELECT_KEYS},
                                            where="1=1", objectIds=",".join(map(str, c))), post=True).get("features", [])
            check_chunk(fs, c, oid)
            return fs
        chunks = [ids[i:i + page] for i in range(0, len(ids), page)]
        if workers > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(workers) as ex: pages = list(ex.map(chunk, chunks))
        else:
            pages = [chunk(c) for c in chunks]
        feats = [f for p in pages for f in p]
    else:
        base["orderByFields"] = query.get("orderByFields", oid)
        feats = page_through(lambda o, n: _get(url + "/query", dict(base, resultOffset=o, resultRecordCount=n)), page)
        got = [(f.get("properties") or {}).get(oid, f.get("id")) for f in feats]
        if None not in got and len(set(got)) != len(got):
            raise RuntimeError(f"repeated features across pages: {len(got) - len(set(got))}")
    n = _get(url + "/query", dict(sel, returnCountOnly="true", f="json")).get("count")
    if n is not None and n != len(feats):
        raise RuntimeError(f"incomplete download: {len(feats)} features of {n}")
    if added:
        for f in feats: (f.get("properties") or {}).pop(oid, None)
    return feats
