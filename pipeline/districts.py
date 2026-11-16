"""Official district (territorial authority) boundaries from Stats NZ, for the national index (T-102, review 26).

LINZ publishes no district boundaries on its open services, so without these the national build works each parcel's
district out from addresses and localities, which is wrong for about a quarter of remote parcels. Stats NZ publishes
the boundaries on its Datafinder (CC BY 4.0), which needs a key: the STATSNZ_API_KEY GitHub secret.

Usage: districts.py OUT_DIR. Finds the newest "Territorial Authority YYYY" layer (full extent, not clipped to the
coast, so islands and foreshore are covered; Stats NZ also has "Area Outside Territorial Authority"), downloads it in
NZTM2000 and writes OUT_DIR/districts.parquet (name, code, wkb) and OUT_DIR/districts.json (layer, title, fetched,
licence, count). Without the key it writes nothing and exits 0: the build then keeps its address-based rule.
"""
import json, os, re, sys
import requests, shapely
from shapely.geometry import shape

API = "https://datafinder.stats.govt.nz/services/api/v1.x"
LICENCE = "Stats NZ, CC BY 4.0"
TITLE = re.compile(r"^Territorial Authority (\d{4})$")   # not "... Clipped", not "... (generalised)"


def _key():
    return os.environ.get("STATSNZ_API_KEY")


def _safe(msg):
    return str(msg).replace(_key() or "\0", "***")


def find_layer(session):
    """(layer id, title, year) of the newest full-detail territorial authority layer."""
    r = session.get(API + "/data/", params=dict(q="Territorial Authority", kind="vector", page_size=100), timeout=120)
    if r.status_code >= 400: raise RuntimeError(_safe(f"Datafinder search refused: {r.status_code} {r.text[:300]}"))
    best = None
    for item in r.json():
        m = TITLE.match((item.get("title") or "").strip())
        if m and (best is None or int(m.group(1)) > best[2]): best = (item["id"], item["title"].strip(), int(m.group(1)))
    if best is None: raise RuntimeError("no 'Territorial Authority YYYY' layer found on the Datafinder")
    return best


def name_field(props):
    """The district name field: TA2025_V1_00_NAME and the like (not the ..._NAME_ASCII copy)."""
    names = [k for k in props if k.upper().endswith("_NAME") and not k.upper().endswith("ASCII_NAME")]
    if not names: raise RuntimeError(f"no name field among {sorted(props)}")
    return names[0]


def download(session, layer):
    """GeoJSON features of the layer in NZTM2000, through the Datafinder's WFS."""
    url = f"https://datafinder.stats.govt.nz/services;key={_key()}/wfs"
    r = session.get(url, params=dict(service="WFS", version="2.0.0", request="GetFeature", typeNames=f"layer-{layer}",
                                     outputFormat="json", srsName="EPSG:2193"), timeout=1800)
    if r.status_code >= 400: raise RuntimeError(_safe(f"Datafinder download refused: {r.status_code} {r.text[:300]}"))
    return r.json()["features"]


def main(out):
    if not _key(): print("STATSNZ_API_KEY not set: no district boundaries; the build keeps its address-based rule"); return
    import pyarrow as pa, pyarrow.parquet as pq
    from provenance import utc_now
    s = requests.Session(); s.headers["Authorization"] = "key " + _key()
    layer, title, year = find_layer(s)
    feats = [f for f in download(s, layer) if f.get("geometry")]
    nf = name_field(feats[0]["properties"]); cf = nf[:-5] if nf.upper().endswith("_NAME") else None
    names = [f["properties"][nf] for f in feats]
    codes = [str(f["properties"].get(cf)) if cf else None for f in feats]
    wkbs = [shapely.to_wkb(shapely.make_valid(shape(f["geometry"]))) for f in feats]
    os.makedirs(out, exist_ok=True)
    pq.write_table(pa.table(dict(name=names, code=codes, wkb=pa.array(wkbs, pa.binary()))), os.path.join(out, "districts.parquet"))
    meta = dict(layer=layer, title=title, url=f"https://datafinder.stats.govt.nz/layer/{layer}/", fetched=utc_now(),
                licence=LICENCE, count=len(feats))
    json.dump(meta, open(os.path.join(out, "districts.json"), "w"), indent=1)
    print(json.dumps(meta), sorted(set(names))[:5], "...")


if __name__ == "__main__":
    main(sys.argv[1])
