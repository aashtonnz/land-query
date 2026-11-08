"""Read the fetch window from LINZ elevation COGs (s3://nz-elevation, CC BY 4.0) without downloading whole files."""
import json, os, sys, time, hashlib
from provenance import utc_now
import tile_env as te
import numpy as np, requests, rasterio
from rasterio.windows import from_bounds
from rasterio.merge import merge

BASE = "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/wellington/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
TILE = te.lidar_bbox(OUT)  # fetch window plus LIDAR_CONTEXT_M on every side
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")
lon0, lat0, lon1, lat1 = te.ll_envelope(TILE)

from lidar_catalogue import NoCoverage, get_json, source_entry


def items_for(coll):
    c = get_json(BASE + coll + "/collection.json")
    hrefs = []
    for l in c["links"]:
        if l.get("rel") != "item": continue
        it = get_json(BASE + coll + "/" + l["href"].lstrip("./"))
        b = it["bbox"]  # WGS84
        if b[0] <= lon1 and b[2] >= lon0 and b[1] <= lat1 and b[3] >= lat0:
            a = it["assets"]["visual"] if "visual" in it["assets"] else next(iter(it["assets"].values()))
            href = a["href"]
            if href.startswith("./"): href = BASE + coll + "/" + href[2:]
            hrefs.append(href)
    return c, hrefs

def read(coll, name):
    t0 = time.time()
    c, hrefs = items_for(coll)
    if not hrefs: raise NoCoverage("no LiDAR survey in this collection covers the window")
    cache = os.path.join(OUT, "cache"); os.makedirs(cache, exist_ok=True)
    local = []
    for h in hrefs:
        p = os.path.join(cache, coll.replace("/", "_") + "_" + os.path.basename(h))
        for attempt in range(4):  # retry dropped connections; write to a temporary name so a broken download never counts as cached (T-60)
            if os.path.exists(p): break
            try:
                with requests.get(h, stream=True, timeout=300) as r:
                    r.raise_for_status()
                    with open(p + ".part", "wb") as f:
                        for chunk in r.iter_content(1 << 20): f.write(chunk)
                os.replace(p + ".part", p)
            except requests.exceptions.RequestException:
                if attempt == 3: raise
                time.sleep(10 * (attempt + 1))
        local.append(p)
    srcs = [rasterio.open(p) for p in local]
    arr, tr = merge(srcs, bounds=TILE, res=1.0, nodata=np.nan, dtype="float32")
    arr = arr[0]
    prof = dict(driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1, dtype="float32",
                crs="EPSG:2193", transform=tr, nodata=np.nan, compress="deflate")
    path = os.path.join(OUT, "raw", name + ".tif")
    with rasterio.open(path, "w", **prof) as d: d.write(arr, 1)
    meta = dict(collection=BASE + coll + "/collection.json", items=hrefs, title=c.get("title"),
                licence=(c.get("license") or "") + " " + json.dumps([p.get("name") for p in c.get("providers", [])]),
                shape=list(arr.shape), valid_frac=float(np.isfinite(arr).mean()),
                sha256=hashlib.sha256(arr.tobytes()).hexdigest(), seconds=round(time.time() - t0, 1), fetched=utc_now())
    print(name, meta["shape"], "valid", round(meta["valid_frac"], 3), meta["seconds"], "s", len(hrefs), "COGs")
    return meta

prov_path = os.path.join(OUT, "provenance.json")
prov = json.load(open(prov_path))
from councils import COUNCIL as C
for coll, name in C.LIDAR:  # the council's surveys (T-86)
    prov["sources"][name] = e = source_entry(read, coll, name)  # no coverage (hills, Kapiti Island) is not a failure
    if not e["ok"]: print(name, "no coverage" if e.get("no_coverage") else "FAILED " + e["error"])
json.dump(prov, open(prov_path, "w"), indent=1)
