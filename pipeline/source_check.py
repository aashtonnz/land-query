"""Weekly source-change check (T-25): record each source's fields, record count and last-edit date, and flag changes.

Usage: source_check.py OUT_JSON [PREVIOUS_JSON]. Writes the snapshot to OUT_JSON and a summary of differences from
PREVIOUS_JSON to OUT_JSON's folder as changes.md; exits 3 when anything changed, so the workflow can flag it. Counts
are within the district's extent. LINZ layers are counted only when LINZ_API_KEY is set (GitHub runs).
"""
import hashlib, json, os, sys, time
import requests
from layers import ARCGIS
from provenance import utc_now

DISTRICT = (1752000, 5452000, 1808000, 5498000)  # NZTM2000: the 46 blocks plus their windows
KC = "https://maps.kapiticoast.govt.nz/server/rest/services/Public"
EXTRA = {"parcels_mirror": f"{KC}/Cadastral/MapServer/0", "district_boundary": f"{KC}/Cadastral/MapServer/1"}
LINZ = {"linz_parcels": 50823, "titles": 50804, "nonprimary_parcels": 50782}
STAC = {
    "dem_2025": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/wellington/kapiti-coast_2024-2025/dem_1m/2193/collection.json",
    "dsm_2025": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/wellington/kapiti-coast_2024-2025/dsm_1m/2193/collection.json",
    "dem_2021": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/wellington/kapiti-coast_2021/dem_1m/2193/collection.json",
    # national catalogues change whenever any survey in New Zealand is added: recorded, never flagged (T-59)
    "nz_dem_1m": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/new-zealand/new-zealand/dem_1m/2193/collection.json",
    "nz_dem_8m": "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/new-zealand/new-zealand-contour/dem_8m/2193/collection.json",
}


def get(url, **params):
    for k in range(4):
        try:
            r = requests.get(url, params=params, timeout=90); r.raise_for_status(); return r
        except requests.RequestException as e:
            if k == 3: raise RuntimeError(str(e).replace(os.environ.get("LINZ_API_KEY", "\0"), "***")[:200]) from None
            time.sleep(5 * (k + 1))


def arcgis(url):
    m = get(url, f="json").json()
    if "error" in m: raise RuntimeError(m["error"])
    env = ",".join(map(str, DISTRICT))
    n = get(url + "/query", where="1=1", geometry=env, geometryType="esriGeometryEnvelope", inSR=2193,
            spatialRel="esriSpatialRelIntersects", returnCountOnly="true", f="json").json().get("count")
    ei = m.get("editingInfo") or {}
    return dict(name=m.get("name"), fields=sorted(f"{f['name']}:{f['type'].replace('esriFieldType', '')}" for f in m.get("fields") or []),
                count=n, last_edit=ei.get("dataLastEditDate") or ei.get("lastEditDate"))


def linz(layer):
    key = os.environ.get("LINZ_API_KEY")
    if not key: return None
    b = f"{DISTRICT[1]},{DISTRICT[0]},{DISTRICT[3]},{DISTRICT[2]},urn:ogc:def:crs:EPSG::2193"
    r = get(f"https://data.linz.govt.nz/services;key={key}/wfs", service="WFS", version="2.0.0", request="GetFeature",
            typeNames=f"layer-{layer}", bbox=b, resultType="hits")
    import re
    m = re.search(r'numberMatched="(\d+)"', r.text)
    return dict(count=int(m.group(1)) if m else None)


def stac(url):
    t = get(url).text; j = json.loads(t)
    return dict(items=sum(1 for l in j.get("links", []) if l.get("rel") == "item"), sha256=hashlib.sha256(t.encode()).hexdigest())


def mirror_gap():
    """LINZ primary parcels inside the district (representative point within KCDC's boundary, closed at sea) that KCDC's
    mirror lacks, by parcel intent, with examples (T-60). Needs LINZ_API_KEY."""
    import linz
    from collections import Counter
    from shapely.geometry import shape
    from overlays import district_polygon
    import arcgis as ag
    if not linz.KEY: return None
    edge = ag.query_all(EXTRA["district_boundary"], dict(where="1=1", outFields="OBJECTID", outSR=2193))
    district = district_polygon([shape(f["geometry"]) for f in edge if f.get("geometry")])
    mirror = {f["properties"].get("id") for f in ag.query_all(EXTRA["parcels_mirror"], dict(where="1=1", outFields="id", outSR=2193, returnGeometry="false"))}
    gap = []
    for f in linz.wfs(50823, DISTRICT):
        if not f.get("geometry") or f["properties"].get("id") in mirror: continue
        if district.contains(shape(f["geometry"]).representative_point()):
            gap.append(dict(id=f["properties"].get("id"), appellation=f["properties"].get("appellation"), intent=f["properties"].get("parcel_intent")))
    return dict(count=len(gap), by_intent=dict(Counter(g["intent"] for g in gap).most_common()), examples=gap[:30], mirror=len(mirror))


def snapshot():
    out = {}
    try:
        g = mirror_gap()
        if g is not None: out["linz_not_in_mirror"] = dict(kind="gap", **g)
    except Exception as e: out["linz_not_in_mirror"] = dict(kind="gap", error=str(e)[:200])
    for name, (url, _) in list(ARCGIS.items()) + [(k, (v, None)) for k, v in EXTRA.items()]:
        try: out[name] = dict(kind="arcgis", url=url, **arcgis(url))
        except Exception as e: out[name] = dict(kind="arcgis", url=url, error=str(e)[:200])
    for name, lid in LINZ.items():
        try:
            v = linz(lid)
            if v is not None: out[name] = dict(kind="linz", layer=lid, **v)
        except Exception as e: out[name] = dict(kind="linz", layer=lid, error=str(e)[:200])
    for name, url in STAC.items():
        try: out[name] = dict(kind="stac", url=url, **stac(url))
        except Exception as e: out[name] = dict(kind="stac", url=url, error=str(e)[:200])
    return out


INFO_ONLY = {"nz_dem_1m", "nz_dem_8m"}


def compare(old, new):
    """Plain-language list of differences between two snapshots (sources in INFO_ONLY are not compared)."""
    out = []
    for k in sorted((set(old) | set(new)) - INFO_ONLY):
        a, b = old.get(k), new.get(k)
        if a is None: out.append(f"- `{k}`: new in the check"); continue
        if b is None: out.append(f"- `{k}`: no longer checked"); continue
        if b.get("error") and not a.get("error"): out.append(f"- `{k}`: could not be read ({b['error']})"); continue
        if a.get("error") and not b.get("error"): out.append(f"- `{k}`: readable again")
        fa, fb = set(a.get("fields") or []), set(b.get("fields") or [])
        if fa and fb and fa != fb:
            out.append(f"- `{k}`: fields changed (added {sorted(fb - fa) or 'none'}, removed {sorted(fa - fb) or 'none'})")
        for f in ("count", "items"):
            if a.get(f) is not None and b.get(f) is not None and a[f] != b[f]:
                pct = 100 * (b[f] - a[f]) / a[f] if a[f] else float("inf")
                out.append(f"- `{k}`: {f} {a[f]} → {b[f]} ({pct:+.1f}%)")
        if a.get("last_edit") != b.get("last_edit") and b.get("last_edit"):
            out.append(f"- `{k}`: data edited (last edit {time.strftime('%Y-%m-%d', time.gmtime(b['last_edit'] / 1000))})")
        if a.get("sha256") and b.get("sha256") and a["sha256"] != b["sha256"] and a.get("items") == b.get("items"):
            out.append(f"- `{k}`: catalogue changed (same number of items)")
    return out


if __name__ == "__main__":
    out = sys.argv[1]; prev = sys.argv[2] if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else None
    snap = dict(checked=utc_now(), sources=snapshot())
    json.dump(snap, open(out, "w"), indent=1, sort_keys=True)
    errors = [k for k, v in snap["sources"].items() if v.get("error")]
    changes = compare(json.load(open(prev))["sources"], snap["sources"]) if prev else []
    md = [f"# Source check {snap['checked']}", "", f"{len(snap['sources'])} sources checked; {len(errors)} unreadable.", ""]
    md += (["Changes since the previous check:", ""] + changes) if changes else (["No changes since the previous check."] if prev else ["First snapshot."])
    if errors: md += ["", "Unreadable this week (flagged every week until fixed):", ""] + [f"- `{k}`: {snap['sources'][k]['error']}" for k in errors]
    open(os.path.join(os.path.dirname(os.path.abspath(out)), "changes.md"), "w").write("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(3 if changes or errors else 0)
