"""The parcel report on demand (T-101, D-21): the full 1 m analysis for one parcel anywhere in New Zealand.

Runs the council pipeline with the national settings (councils/national.py: LINZ data only, LINZ's national 1 m LiDAR
mosaics) on a block around one parcel, then writes that parcel's row with the LiDAR surveys it rests on.

Usage: parcel_report.py OUT_DIR (--id PARCEL_ID | --address "FULL ADDRESS"). Writes OUT_DIR/report.json (the parcel's
values, the surveys and the provenance) and keeps the run's working files in OUT_DIR/data. Needs no key; with
LINZ_API_KEY set, parcels, titles and easements come from the LINZ Data Service.
"""
import argparse, json, math, os, subprocess, sys, time
import requests
from shapely.geometry import shape

HERE = os.path.dirname(os.path.abspath(__file__))
SVC = "https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services"
PARCELS = f"{SVC}/LINZ_NZ_Primary_Parcels/FeatureServer/0/query"
ADDRESSES = f"{SVC}/LINZ_NZ_Addresses/FeatureServer/0/query"
ELEV = "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/new-zealand/new-zealand/"
MAX_SIDE = 3000      # metres: larger parcels need more memory than a report run should take
STEPS = ["fetch_parcels_kcdc.py", "fetch_tile.py", "fetch_lidar.py", "fetch_parcels.py", "compile_tile.py"]


def q(url, **params):
    r = requests.get(url, params=dict(params, f="geojson"), timeout=120); r.raise_for_status()
    j = r.json()
    if "error" in j: raise RuntimeError(j["error"])
    return j.get("features", [])


def find_parcel(pid=None, address=None):
    """(parcel id, its LINZ ArcGIS feature, the address used if any). An address is matched exactly, ignoring case."""
    if address is not None:
        a = address.replace("'", "''").strip()
        fs = q(ADDRESSES, where=f"UPPER(full_address)=UPPER('{a}')", outFields="full_address", outSR=2193)
        if not fs: raise SystemExit(f"no LINZ address {address!r}")
        x, y = fs[0]["geometry"]["coordinates"]
        ps = [f for f in q(PARCELS, geometry=f"{x},{y}", geometryType="esriGeometryPoint", inSR=2193,
                           spatialRel="esriSpatialRelIntersects", outFields="*", outSR=2193)
              if f["properties"].get("parcel_intent") not in ("Road", "Hydro")]
        if not ps: raise SystemExit(f"no parcel under the address point of {address!r}")
        return ps[0]["properties"]["id"], ps[0], fs[0]["properties"]["full_address"]
    fs = q(PARCELS, where=f"id={int(pid)}", outFields="*", outSR=2193)
    if not fs: raise SystemExit(f"no LINZ primary parcel {pid}")
    return int(pid), fs[0], None


def block_for(g):
    """(xmin, ymin, size): a square block holding the whole parcel, so its representative point is inside."""
    x0, y0, x1, y1 = g.bounds
    side = max(x1 - x0, y1 - y0)
    if side > MAX_SIDE: raise SystemExit(f"parcel is {side:.0f} m across; reports are limited to {MAX_SIDE} m")
    size = int(math.ceil((side + 4) / 10.0) * 10)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return int(math.floor(cx - size / 2)), int(math.floor(cy - size / 2)), size


def _reproject(g, src, dst):
    import numpy as np, shapely
    from pyproj import Transformer
    t = Transformer.from_crs(src, dst, always_xy=True)
    return shapely.transform(g, lambda xy: np.column_stack(t.transform(xy[:, 0], xy[:, 1])))


def surveys(g, product):
    """LiDAR surveys in the national mosaic under the parcel: [{survey, flown_from, flown_to, ..., share_pct}],
    largest share first, from the collection's capture-dates file (survey boundaries, simplified by LINZ)."""
    fc = requests.get(ELEV + f"{product}/2193/capture-dates.geojson", timeout=120).json()
    gl = _reproject(g, 2193, 4326)
    out = []
    for f in fc["features"]:
        s = shape(f["geometry"])
        if not s.intersects(gl): continue
        a = _reproject(s.intersection(gl), 4326, 2193).area
        if a <= 0: continue
        p = f["properties"]
        out.append(dict(survey=p.get("title"), flown_from=p.get("flown_from"), flown_to=p.get("flown_to"),
                        producer=p.get("producer"), licensor=p.get("licensor"), licence=p.get("license"),
                        collection=p.get("source"), share_pct=round(100 * a / g.area, 1)))
    return sorted(out, key=lambda d: -d["share_pct"])


def run(out, pid=None, address=None):
    t0 = time.time()
    pid, feat, addr = find_parcel(pid, address)
    g = shape(feat["geometry"])
    x, y, size = block_for(g)
    data = os.path.join(out, "data"); os.makedirs(os.path.join(data, "raw"), exist_ok=True)
    env = dict(os.environ, COUNCIL="national", TILE_XMIN=str(x), TILE_YMIN=str(y), TILE_SIZE=str(size))
    log = open(os.path.join(out, "run.log"), "w")
    timings = {}
    for step in ["district_flow.py"] + STEPS:
        t = time.time()
        args = [sys.executable, os.path.join(HERE, step)]
        args += [os.path.join(data, "raw", "district_flow.tif")] if step == "district_flow.py" else [data]
        r = subprocess.run(args, env=env, cwd=HERE, stdout=log, stderr=subprocess.STDOUT)
        timings[step] = round(time.time() - t, 1)
        if r.returncode: raise SystemExit(f"{step} failed; see {log.name}")
    import pandas as pd
    df = pd.read_parquet(os.path.join(data, "units.parquet"))
    row = df[df.unit_id == pid]
    if len(row) != 1: raise SystemExit(f"parcel {pid} not compiled ({len(row)} rows); see {log.name}")
    vals = {k: (None if (isinstance(v, float) and v != v) else (v.item() if hasattr(v, "item") else v))
            for k, v in row.iloc[0].to_dict().items()}
    prov = json.load(open(os.path.join(data, "provenance.json")))
    from shapely.geometry import mapping
    near = g.buffer(10)
    blds = [mapping(b) for b in (shape(f["geometry"]) for f in json.load(open(os.path.join(data, "raw", "linz_buildings.geojson")))["features"]
                                 if f.get("geometry")) if b.intersects(near)]
    rep = dict(parcel_id=pid, address=addr, block=[x, y, size], values=vals,
               geometry=mapping(g), buildings_nearby=blds,
               lidar_surveys=dict(dem=surveys(g, "dem_1m"), dsm=surveys(g, "dsm_1m")),
               sources=prov.get("sources"), seconds=round(time.time() - t0), step_seconds=timings)
    json.dump(rep, open(os.path.join(out, "report.json"), "w"), indent=1, default=str)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--id", type=int); ap.add_argument("--address")
    a = ap.parse_args()
    if (a.id is None) == (a.address is None): ap.error("give --id or --address")
    r = run(a.out, a.id, a.address)
    print(json.dumps(dict(parcel_id=r["parcel_id"], seconds=r["seconds"], steps=r["step_seconds"],
                          dem=r["lidar_surveys"]["dem"][:2], values=len(r["values"]))))
