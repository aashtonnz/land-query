"""Download every layer the national index reads once, for the whole country, before the tile jobs start (T-102).

The tile jobs then read local files (national_index.fetch with NI_BULK set) and make no requests to LINZ, so they can
run many at a time without meeting a rate limit. The four big layers come as whole-layer exports from the LINZ Data
Service (one request each, needs LINZ_API_KEY, held only as a GitHub secret); the small ones (coast, lakes, rivers, the
land outline, localities) from the same LINZ ArcGIS services as before, once each. Only the fields the index uses are
kept: the titles export also carries owner counts and estate descriptions, which are dropped here, never stored (D-12).

Each layer is written as DIR/{layer}.parquet: its fields, the geometry as WKB (NZTM2000) and its bounding box, sorted
by 40 km tile so a job reads only the row groups near its tile. DIR/manifest.json records the source, layer, fetch time
and record count of each, and the count the ArcGIS service reports, for the check that both hold the same data.

Usage: bulk.py DIR
"""
import io, json, math, os, sqlite3, struct, sys, tempfile, time, zipfile
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, requests, shapely
from shapely.geometry import shape

import arcgis
import national_index as N
from provenance import utc_now

LDS_API = "https://data.linz.govt.nz/services/api/v1.x"
# layer: (LINZ Data Service layer, {our field: export field}); geometry is read from the GeoPackage
LDS_LAYERS = dict(
    parcels=(50823, dict(id="id", appellation="appellation", parcel_intent="parcel_intent", topology_type="topology_type",
                         land_district="land_district", titles="titles", survey_area="survey_area", calc_area="calc_area")),
    titles=(50804, dict(title_no="title_no", status="status", type="type")),          # never owners, their number or the estate text
    nonprimary=(50782, dict(id="id", parcel_intent="parcel_intent")),   # easements and covenants (T-102); no title references kept
    buildings=(101290, dict(building_id="building_id", use_="use", capture_source_to="capture_source_to")),
    # addresses: the Data Service's layer 105689 no longer exists (16 Nov 2026), so they come from the ArcGIS service
)
SERVICE_LAYERS = ["coast", "lakes", "rivers", "land", "localities", "addresses"]   # from the ArcGIS services, once each
BLOCKED = {"addresses"}   # asked in 80 km blocks: the service gives up on a query running past about 55 s


def _key():
    k = os.environ.get("LINZ_API_KEY")
    if not k: sys.exit("LINZ_API_KEY not set (it is a GitHub repository secret; run this on GitHub)")
    return k


def _safe(msg):
    return str(msg).replace(os.environ.get("LINZ_API_KEY") or "\0", "***")


def lds_export(layer, out_dir, timeout=3600):
    """Path of the GeoPackage of a whole LINZ Data Service layer in NZTM2000, exported and downloaded."""
    h = {"Authorization": "key " + _key()}
    r = requests.post(LDS_API + "/exports/", headers=h, timeout=120, json=dict(
        crs="EPSG:2193", formats=dict(vector="application/x-ogc-gpkg"), items=[dict(item=f"{LDS_API}/layers/{layer}/")]))
    if r.status_code >= 400: raise RuntimeError(_safe(f"export of layer {layer} refused: {r.status_code} {r.text[:300]}"))
    job = r.json(); t0 = time.time()
    while job.get("state") not in ("complete", "error", "cancelled"):
        if time.time() - t0 > timeout: raise RuntimeError(f"export of layer {layer} not ready after {timeout} s")
        time.sleep(15)
        job = requests.get(job["url"], headers=h, timeout=120).json()
    if job["state"] != "complete": raise RuntimeError(f"export of layer {layer}: {job['state']}")
    path = os.path.join(out_dir, f"lds-{layer}.zip")
    with requests.get(job["download_url"], headers=h, stream=True, timeout=600) as d:
        d.raise_for_status()
        with open(path, "wb") as f:
            for chunk in d.iter_content(1 << 22): f.write(chunk)
    with zipfile.ZipFile(path) as z:
        gp = [n for n in z.namelist() if n.endswith(".gpkg")]
        if len(gp) != 1: raise RuntimeError(f"export of layer {layer}: expected one GeoPackage, found {gp}")
        z.extract(gp[0], out_dir)
    os.remove(path)
    return os.path.join(out_dir, gp[0])


def gpkg_wkb(blob):
    """The WKB inside a GeoPackage geometry blob (its header holds an envelope whose size the flags give)."""
    if blob is None or blob[:2] != b"GP": return None
    env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(blob[3] >> 1) & 7]
    return bytes(blob[8 + env:])


def read_gpkg(path, fields):
    """Columns {our field: list} and the WKB list of the GeoPackage's one feature table; fails if a field is missing."""
    con = sqlite3.connect(path)
    table, geom = con.execute("SELECT table_name, column_name FROM gpkg_geometry_columns").fetchone()
    have = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]
    missing = [f for f in fields.values() if f not in have]
    if missing: raise RuntimeError(f"{os.path.basename(path)}: fields {missing} not in the export (has {have})")
    cols = ", ".join(f'"{f}"' for f in fields.values())
    out = {k: [] for k in fields}; wkbs = []
    for row in con.execute(f'SELECT {cols}, "{geom}" FROM "{table}"'):
        for k, v in zip(fields, row): out[k].append(v)
        wkbs.append(gpkg_wkb(row[-1]))
    return out, wkbs


def write_layer(path, cols, geoms_wkb):
    """DIR/{layer}.parquet: fields, wkb and bounding box, sorted by 40 km tile (row groups of 20,000)."""
    g = shapely.from_wkb(np.array(geoms_wkb, dtype=object))
    ok = ~shapely.is_missing(g)
    b = shapely.bounds(g)
    cx, cy = (b[:, 0] + b[:, 2]) / 2, (b[:, 1] + b[:, 3]) / 2
    order = np.lexsort(((cx - N.ORIGIN[0]) // N.TILE, (cy - N.ORIGIN[1]) // N.TILE))
    order = order[ok[order]]
    data = {k: pa.array([v[i] for i in order]) for k, v in cols.items()}
    data.update(wkb=pa.array([geoms_wkb[i] for i in order], pa.binary()),
                xmin=b[order, 0], ymin=b[order, 1], xmax=b[order, 2], ymax=b[order, 3])
    pq.write_table(pa.table(data), path, compression="zstd", row_group_size=20000)
    return int(ok.sum())


def count_titles(titles, current):
    """(titles listed per parcel, how many of them are not current) from each parcel's comma-separated title list."""
    n, missing = [], []
    for t in titles:
        tnos = [x.strip() for x in (t or "").split(",") if x.strip()]
        n.append(len(tnos)); missing.append(sum(x not in current for x in tnos))
    return n, missing


def blocks(url, fields, key, step=80_000, where="1=1"):
    """Every feature of a layer matching `where`, asked in step-sized blocks where the national index has tiles (four
    at a time); a feature reaching over a block edge is kept once, by its key."""
    from concurrent.futures import ThreadPoolExecutor
    tiles = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "nz_tiles.json")))
    boxes = sorted({(math.floor(t[0] / step) * step, math.floor(t[1] / step) * step) for t in tiles})
    ask = lambda b: arcgis.query_all(url, dict(where=where, geometry=f"{b[0]},{b[1]},{b[0] + step},{b[1] + step}", geometryType="esriGeometryEnvelope",
                                               inSR=2193, spatialRel="esriSpatialRelIntersects", outFields=fields, outSR=2193), workers=2)
    with ThreadPoolExecutor(4) as ex: got = list(ex.map(ask, boxes))
    seen, out = set(), []
    for fs in got:
        for f in fs:
            k = (f.get("properties") or {}).get(key)
            if k is not None and k in seen: continue
            seen.add(k); out.append(f)
    return out


def service_intents():
    """{parcel intent: parcels} on LINZ's parcel service, in one grouped count: every kind it holds."""
    url = N.SVC + N.LAYERS["parcels"][0] + "/FeatureServer/0/query"
    r = arcgis._get(url, dict(where="1=1", groupByFieldsForStatistics="parcel_intent", f="json",
                              outStatistics=json.dumps([dict(statisticType="count", onStatisticField="id", outStatisticFieldName="n")])))
    out = {f["attributes"]["parcel_intent"]: f["attributes"]["n"] for f in r.get("features", [])}
    if not out: raise RuntimeError(f"the parcel service gave no counts by intent: {str(r)[:300]}")
    return out


def intent_check(intents, fail=True, service=None):
    """{parcel intent: (records in the export, records in the service)} and the kinds short in the export; with fail,
    exits if any is, or if the total is short. Every kind the service holds is compared, not only those in the export:
    LINZ's export of layer 50823 holds no road or hydro parcels, and no parcels of three "Vesting on Deposit" kinds
    (348 parcels, review 27). The service holds about 6,000 parcels twice."""
    from collections import Counter
    got = Counter(intents); svc = service if service is not None else service_intents()
    out = {str(k): (got.get(k, 0), svc.get(k, 0)) for k in set(got) | set(svc)}
    print("parcels by intent (export, service):", dict(sorted(out.items())), flush=True)
    short = {k: v for k, v in out.items() if v[0] < v[1] - max(50, 0.01 * v[1]) or (v[0] == 0 and v[1] > 0)}
    total = (sum(got.values()), sum(svc.values()))
    if fail and (short or total[0] < total[1] - max(1000, 0.003 * total[1])):
        sys.exit(f"the parcels export is short (export, service): {short or total}")
    return out, short


def add_from_service(cols, wkbs, kinds):
    """Replace the export's parcels of these kinds with the service's, asked in blocks: (cols, wkbs, how many added)."""
    keep = [i for i, k in enumerate(cols["parcel_intent"]) if k not in kinds]
    cols = {k: [v[i] for i in keep] for k, v in cols.items()}; wkbs = [wkbs[i] for i in keep]
    svc, fields, _ = N.LAYERS["parcels"]
    where = "parcel_intent IN (" + ", ".join("'" + k.replace("'", "''") + "'" for k in sorted(kinds)) + ")"
    have = set(cols["id"])   # a parcel the export holds under another intent is not taken twice (review 27)
    feats = [f for f in blocks(N.SVC + svc + "/FeatureServer/0", fields, N.KEYS["parcels"], where=where)
             if f.get("geometry") and f["properties"].get("id") not in have]
    for k in cols: cols[k] += [f["properties"].get(k) for f in feats]
    wkbs += [shapely.to_wkb(shape(f["geometry"])) for f in feats]
    return cols, wkbs, len(feats)


def service_count(layer):
    svc = N.LAYERS[layer][0]
    return arcgis._get(N.SVC + svc + "/FeatureServer/0/query", dict(where="1=1", returnCountOnly="true", f="json"))["count"]


def main(out):
    os.makedirs(out, exist_ok=True); manifest = {}
    current = None
    for layer in ["titles", "parcels", "nonprimary", "buildings"]:
        lds, fields = LDS_LAYERS[layer]
        t0 = time.time()
        with tempfile.TemporaryDirectory(dir=out) as tmp:
            cols, wkbs = read_gpkg(lds_export(lds, tmp), fields)
        # the bulk files are passed to the tile jobs as an artifact, which anyone signed in to GitHub can fetch from a
        # public repository: so no title reference is written. Each parcel's titles are counted here, against the
        # current titles (live or partly cancelled), and only the two counts go on (D-15, T-106)
        if layer == "titles":
            current = {t for t, st in zip(cols["title_no"], cols["status"]) if st in ("LIVE", "PRTC")}
            manifest[layer] = dict(source=f"LINZ Data Service layer {lds} (whole-layer export); counted per parcel, not kept",
                                   url=N.LDS + str(lds), fetched=utc_now(), records=len(cols["title_no"]),
                                   service_records=service_count(layer), seconds=round(time.time() - t0))
            print(layer, manifest[layer], flush=True); del cols, wkbs; continue
        if layer == "parcels":
            by_intent, short = intent_check(cols["parcel_intent"], fail=False)
            if short:   # kinds the export leaves out (roads, hydro): from the service, then checked again
                cols, wkbs, added = add_from_service(cols, wkbs, set(short))
                print(f"{added} parcels of {sorted(short)} from the service", flush=True)
                by_intent, _ = intent_check(cols["parcel_intent"])
            cols["title_count"], cols["titles_not_found"] = count_titles(cols.pop("titles"), current); current = None
        n = write_layer(os.path.join(out, layer + ".parquet"), cols, wkbs); del cols, wkbs
        manifest[layer] = dict(source=f"LINZ Data Service layer {lds} (whole-layer export)", url=N.LDS + str(lds),
                               **(dict(by_intent=by_intent, from_service=sorted(short)) if layer == "parcels" else {}),
                               fetched=utc_now(), records=n, service_records=None if layer == "nonprimary" else service_count(layer), seconds=round(time.time() - t0))
        print(layer, manifest[layer], flush=True)
    assert not os.path.exists(os.path.join(out, "titles.parquet")) and "titles" not in pq.read_schema(os.path.join(out, "parcels.parquet")).names
    for layer in SERVICE_LAYERS:
        t0 = time.time(); svc, fields, lds = N.LAYERS[layer]; opts = N.FETCH_OPTS.get(layer, {})
        url = N.SVC + svc + "/FeatureServer/0"; extra = {k: v for k, v in opts.items() if k != "workers"}
        if layer in BLOCKED:
            feats = blocks(url, fields, N.KEYS[layer])
        else:
            feats = arcgis.query_all(url, dict(where="1=1", outFields=fields, outSR=2193, **extra), workers=opts.get("workers", N.WORKERS))
        feats = [f for f in feats if f.get("geometry")]
        cols = {k: [f["properties"].get(k) for f in feats] for k in fields.split(",")}
        n = write_layer(os.path.join(out, layer + ".parquet"), cols, [shapely.to_wkb(shape(f["geometry"])) for f in feats])
        manifest[layer] = dict(source="LINZ ArcGIS service, whole layer" + (" in 80 km blocks" if layer in BLOCKED else ""), url=url,
                               fetched=utc_now(), records=n, service_records=service_count(layer) if layer in BLOCKED else n,
                               seconds=round(time.time() - t0))
        print(layer, manifest[layer], flush=True)
    # council zoning where it is published under an open licence (T-38): its own provenance in zoning.json
    import zoning
    zm = zoning.fetch_all(out)
    manifest["zoning"] = dict(source="council zoning layers with an open licence (zoning.py)", councils=len(zm),
                              failed=sorted(d for d, m in zm.items() if m.get("failed")), fetched=utc_now())
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    check_counts(manifest)


def check_counts(manifest):
    """The export and the service are the same dataset; they may differ by a few days of edits, never by much. Checked
    for every layer holding both counts: parcels are checked kind by kind (intent_check), non-primary parcels are not
    on the service, and zoning is per council in zoning.json (its entry has no counts: review of 18 Nov)."""
    for layer, m in manifest.items():
        if layer == "parcels" or "records" not in m or m.get("service_records") is None: continue
        if abs(m["records"] - m["service_records"]) > max(100, 0.02 * m["service_records"]):   # the service holds some records twice (once_each)
            sys.exit(f"{layer}: {m['records']} records in the export against {m['service_records']} in the service")


if __name__ == "__main__":
    main(sys.argv[1])
