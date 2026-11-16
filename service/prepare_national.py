"""Turn a national index (T-102) into results the query service reads: prepare_national.py INDEX_DIR OUT_DIR.

INDEX_DIR holds index.parquet, provenance.json and run.json from a national build or release. OUT_DIR gets:
- units.parquet: every column but the shape and title references, with parcel_id as unit_id, the 40 km tile the
  parcel was built in as block_id (named by its south-west corner) and the box around it (bbox_*), for area queries;
- provenance.json: for each source, its address and, per tile, when it was fetched and how many records it held;
  marked "dataset": "national" so the service uses the national catalogue;
- RUN.txt: which build this is.
"""
import json, os, sys
import numpy as np
import pandas as pd
import shapely

TILE = 40_000


def tile_keys(x0s, y0s):
    return [f"{int(x)}_{int(y)}" for x, y in zip(x0s, y0s)]


def prepare(index_dir, out):
    prov = json.load(open(os.path.join(index_dir, "provenance.json")))
    df = pd.read_parquet(os.path.join(index_dir, "index.parquet"))
    df = df.drop(columns=[c for c in ("titles", "title_types") if c in df])   # never served (T-106)
    g = shapely.from_wkb(df.pop("geometry_wkb").values)
    b = shapely.bounds(g)
    df["bbox_xmin"], df["bbox_ymin"], df["bbox_xmax"], df["bbox_ymax"] = b[:, 0], b[:, 1], b[:, 2], b[:, 3]
    # each parcel's tile: the one holding its representative point, as in the build
    tiles = np.array([t["tile"][:2] for t in prov["tiles"]])
    ox, oy = tiles[:, 0].min() % TILE, tiles[:, 1].min() % TILE
    x0 = np.floor((df.rep_x.values - ox) / TILE) * TILE + ox
    y0 = np.floor((df.rep_y.values - oy) / TILE) * TILE + oy
    df.insert(1, "block_id", tile_keys(x0, y0))
    known = set(tile_keys(tiles[:, 0], tiles[:, 1]))
    stray = set(df.block_id) - known
    if stray: sys.exit(f"parcels in tiles the build does not list: {sorted(stray)[:5]}")
    df = df.rename(columns={"parcel_id": "unit_id"})
    os.makedirs(out, exist_ok=True)
    df.to_parquet(os.path.join(out, "units.parquet"), index=False, compression="zstd", row_group_size=100_000)
    sources = {}
    for t in prov["tiles"]:
        key = tile_keys([t["tile"][0]], [t["tile"][1]])[0]
        for k, v in t.items():
            if isinstance(v, list) and v and all(isinstance(x, dict) and "collection" in x for x in v):   # elevation: surveys
                s = sources.setdefault(k, dict(url=None, licence=v[0].get("licence"), by_block={}))
                s["by_block"][key] = [dict(dataset=x.get("title"), collection=x.get("collection"), files=len(x.get("items") or []),
                                           fetched=x.get("fetched")) for x in v]
            if not isinstance(v, dict): continue
            s = sources.setdefault(k, dict(url=v.get("url"), same_as=v.get("same_as"), licence=v.get("licence"), by_block={}))
            s["by_block"][key] = {f: v.get(f) for f in ("fetched", "features", "sha256", "file") if v.get(f) is not None}
    sources["dataset"] = "national"
    sources["build"] = dict(built=prov.get("built"), commit=prov.get("commit"))
    json.dump(sources, open(os.path.join(out, "provenance.json"), "w"))
    run = json.load(open(os.path.join(index_dir, "run.json"))) if os.path.exists(os.path.join(index_dir, "run.json")) else {}
    open(os.path.join(out, "RUN.txt"), "w").write(
        f"National index built {prov.get('built')} from commit {prov.get('commit')}: {len(df):,} parcels in {len(known)} tiles"
        + (f" ({run.get('shares')} shares)" if run.get("shares") else "") + "\n")
    print(f"{len(df):,} parcels, {len(sources) - 2} sources -> {out}")


if __name__ == "__main__":
    prepare(sys.argv[1], sys.argv[2])
