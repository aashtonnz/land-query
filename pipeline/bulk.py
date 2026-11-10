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
import io, json, os, sqlite3, struct, sys, tempfile, time, zipfile
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
    buildings=(101290, dict(building_id="building_id", use_="use", capture_source_to="capture_source_to")),
    addresses=(105689, dict(address_id="address_id", full_address="full_address", address_number="address_number",
                            suburb_locality="suburb_locality", town_city="town_city", territorial_authority="territorial_authority")),
)
SERVICE_LAYERS = ["coast", "lakes", "rivers", "land", "localities"]   # small: from the ArcGIS services, once each


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


def service_count(layer):
    svc = N.LAYERS[layer][0]
    return arcgis._get(N.SVC + svc + "/FeatureServer/0/query", dict(where="1=1", returnCountOnly="true", f="json"))["count"]


def main(out):
    os.makedirs(out, exist_ok=True); manifest = {}
    for layer, (lds, fields) in LDS_LAYERS.items():
        t0 = time.time()
        with tempfile.TemporaryDirectory(dir=out) as tmp:
            cols, wkbs = read_gpkg(lds_export(lds, tmp), fields)
        n = write_layer(os.path.join(out, layer + ".parquet"), cols, wkbs); del cols, wkbs
        manifest[layer] = dict(source=f"LINZ Data Service layer {lds} (whole-layer export)", url=N.LDS + str(lds),
                               fetched=utc_now(), records=n, service_records=service_count(layer), seconds=round(time.time() - t0))
        print(layer, manifest[layer], flush=True)
    for layer in SERVICE_LAYERS:
        t0 = time.time(); svc, fields, lds = N.LAYERS[layer]; opts = N.FETCH_OPTS.get(layer, {})
        feats = arcgis.query_all(N.SVC + svc + "/FeatureServer/0", dict(where="1=1", outFields=fields, outSR=2193,
                                 **{k: v for k, v in opts.items() if k != "workers"}), workers=opts.get("workers", N.WORKERS))
        feats = [f for f in feats if f.get("geometry")]
        cols = {k: [f["properties"].get(k) for f in feats] for k in fields.split(",")}
        n = write_layer(os.path.join(out, layer + ".parquet"), cols, [shapely.to_wkb(shape(f["geometry"])) for f in feats])
        manifest[layer] = dict(source="LINZ ArcGIS service, whole layer", url=N.SVC + svc + "/FeatureServer/0", fetched=utc_now(),
                               records=n, service_records=n, seconds=round(time.time() - t0))
        print(layer, manifest[layer], flush=True)
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    # the export and the service are the same dataset; they may differ by a few days of edits, never by much
    for layer, m in manifest.items():
        if abs(m["records"] - m["service_records"]) > max(100, 0.02 * m["service_records"]):   # the service holds some records twice (once_each)
            sys.exit(f"{layer}: {m['records']} records in the export against {m['service_records']} in the service")


if __name__ == "__main__":
    main(sys.argv[1])
