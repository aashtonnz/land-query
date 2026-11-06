"""Read the fetch window from LINZ elevation COGs (s3://nz-elevation, CC BY 4.0) without downloading whole files."""
import json, os, sys, time, hashlib
import tile_env as te
import numpy as np, requests, rasterio
from rasterio.windows import from_bounds
from rasterio.merge import merge
from pyproj import Transformer

BASE = "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/wellington/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
TILE = te.fetch_bbox(OUT)  # fetch window (block grown to cover its parcels)
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.tiff")
to_ll = Transformer.from_crs(2193, 4326, always_xy=True)
lon0, lat0 = to_ll.transform(TILE[0], TILE[1]); lon1, lat1 = to_ll.transform(TILE[2], TILE[3])

def items_for(coll):
    c = requests.get(BASE + coll + "/collection.json", timeout=60).json()
    hrefs = []
    for l in c["links"]:
        if l.get("rel") != "item": continue
        it = requests.get(BASE + coll + "/" + l["href"].lstrip("./"), timeout=60).json()
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
    cache = os.path.join(OUT, "cache"); os.makedirs(cache, exist_ok=True)
    local = []
    for h in hrefs:
        p = os.path.join(cache, coll.replace("/", "_") + "_" + os.path.basename(h))
        if not os.path.exists(p):
            with requests.get(h, stream=True, timeout=300) as r:
                r.raise_for_status()
                with open(p, "wb") as f:
                    for chunk in r.iter_content(1 << 20): f.write(chunk)
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
                sha256=hashlib.sha256(arr.tobytes()).hexdigest(), seconds=round(time.time() - t0, 1))
    print(name, meta["shape"], "valid", round(meta["valid_frac"], 3), meta["seconds"], "s", len(hrefs), "COGs")
    return meta

prov_path = os.path.join(OUT, "provenance.json")
prov = json.load(open(prov_path))
for coll, name in [("kapiti-coast_2024-2025/dem_1m/2193", "dem_2025"),
                   ("kapiti-coast_2024-2025/dsm_1m/2193", "dsm_2025"),
                   ("kapiti-coast_2021/dem_1m/2193", "dem_2021")]:
    try: prov["sources"][name] = dict(ok=True, **read(coll, name))
    except Exception as e:
        prov["sources"][name] = dict(ok=False, error=str(e)[:300]); print(name, "FAILED", e)
json.dump(prov, open(prov_path, "w"), indent=1)
