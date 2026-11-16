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


def prepare(index_dir, out, batch=200_000):
    """Write OUT/units.parquet a batch at a time, so the whole country fits in about half a gigabyte of memory (read
    whole, it took 5.3 GB: service review, 16 Nov)."""
    import pyarrow as pa, pyarrow.parquet as pq
    prov = json.load(open(os.path.join(index_dir, "provenance.json")))
    # each parcel's tile: the one holding its representative point, as in the build
    tiles = np.array([t["tile"][:2] for t in prov["tiles"]])
    ox, oy = tiles[:, 0].min() % TILE, tiles[:, 1].min() % TILE
    known = set(tile_keys(tiles[:, 0], tiles[:, 1]))
    src = pq.ParquetFile(os.path.join(index_dir, "index.parquet"))
    keep = [c for c in src.schema_arrow.names if c not in ("titles", "title_types", "geometry_wkb")]   # never served (T-106)
    os.makedirs(out, exist_ok=True)
    writer, n = None, 0
    for b in src.iter_batches(batch_size=batch, columns=keep + ["geometry_wkb"]):
        bounds = shapely.bounds(shapely.from_wkb(b.column("geometry_wkb").to_numpy(zero_copy_only=False)))
        rx, ry = b.column("rep_x").to_numpy(zero_copy_only=False), b.column("rep_y").to_numpy(zero_copy_only=False)
        block = tile_keys(np.floor((rx - ox) / TILE) * TILE + ox, np.floor((ry - oy) / TILE) * TILE + oy)
        stray = set(block) - known
        if stray: sys.exit(f"parcels in tiles the build does not list: {sorted(stray)[:5]}")
        cols = {("unit_id" if c == "parcel_id" else c): b.column(c) for c in keep}
        names = list(cols)
        names.insert(1, "block_id")
        cols["block_id"] = pa.array(block, pa.string())
        for k, name in enumerate(("bbox_xmin", "bbox_ymin", "bbox_xmax", "bbox_ymax")):
            cols[name] = pa.array(bounds[:, k], pa.float64()); names.append(name)
        t = pa.table({c: cols[c] for c in names})
        if writer is None:
            schema = pa.schema([f.with_type(pa.string()) if pa.types.is_null(f.type) else f for f in t.schema])   # a column empty in the first batch
            writer = pq.ParquetWriter(os.path.join(out, "units.parquet"), schema, compression="zstd")
        writer.write_table(t.cast(writer.schema), row_group_size=100_000); n += t.num_rows
    writer.close()
    sources = {}
    for t in prov["tiles"]:
        key = tile_keys([t["tile"][0]], [t["tile"][1]])[0]
        for k, v in t.items():
            if isinstance(v, list) and v and all(isinstance(x, dict) and "collection" in x for x in v):   # elevation: surveys
                s = sources.setdefault(k, dict(url=None, licence=v[0].get("licence"), by_block={}))
                s["by_block"][key] = [dict(dataset=x.get("title"), collection=x.get("collection"), files=len(x.get("items") or []),
                                           fetched=x.get("fetched")) for x in v]
            if k == "lakes_rivers" and isinstance(v, int):   # a count only: Topo50 lakes and LINZ river areas in the window
                s = sources.setdefault(k, dict(url=None, licence="LINZ, CC BY 4.0", by_block={}))
                s["by_block"][key] = dict(features=v)
            if not isinstance(v, dict): continue
            s = sources.setdefault(k, dict(url=v.get("url"), same_as=v.get("same_as"), licence=v.get("licence"), by_block={}))
            s["by_block"][key] = {f: v.get(f) for f in ("fetched", "features", "sha256", "file") if v.get(f) is not None}
    sources["dataset"] = "national"
    sources["build"] = dict(built=prov.get("built"), commit=prov.get("commit"))
    json.dump(sources, open(os.path.join(out, "provenance.json"), "w"))
    run = json.load(open(os.path.join(index_dir, "run.json"))) if os.path.exists(os.path.join(index_dir, "run.json")) else {}
    open(os.path.join(out, "RUN.txt"), "w").write(
        f"National index built {prov.get('built')} from commit {prov.get('commit')}: {n:,} parcels in {len(known)} tiles"
        + (f" ({run.get('shares')} shares)" if run.get("shares") else "") + "\n")
    print(f"{n:,} parcels, {len(sources) - 2} sources -> {out}")


if __name__ == "__main__":
    prepare(sys.argv[1], sys.argv[2])
