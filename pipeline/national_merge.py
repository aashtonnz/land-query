"""Merge the shares of a national build (T-102) into one index: national_merge.py SHARES_DIR OUT_DIR N.

Each share is a directory holding index.parquet, provenance.json and run.json from `national_index.py OUT nz TILES K N`.
The merge refuses to write anything unless all N shares are present, every tile in the plan was built once, and no
parcel appears twice, so a published index is never silently partial.
"""
import glob, json, os, sys
import pandas as pd


def merge(shares_dir, out, n, tiles):
    dirs = sorted(os.path.dirname(p) for p in glob.glob(os.path.join(shares_dir, "*", "run.json")))
    if len(dirs) != n: sys.exit(f"{len(dirs)} of {n} shares present: nothing written")
    provs = [json.load(open(os.path.join(d, "provenance.json"))) for d in dirs]
    built = sorted(tuple(t["tile"]) for p in provs for t in p["tiles"])
    if built != sorted(tuple(t) for t in tiles): sys.exit(f"{len(built)} tiles built against {len(tiles)} planned: nothing written")
    df = pd.concat([pd.read_parquet(os.path.join(d, "index.parquet")) for d in dirs], ignore_index=True)
    dup = int(df.parcel_id.duplicated().sum())
    if dup: sys.exit(f"{dup} parcels appear twice: nothing written")
    commits = sorted({p.get("commit") for p in provs})
    if len(commits) != 1: sys.exit(f"shares built from different code {commits}: nothing written")
    os.makedirs(out, exist_ok=True)
    df.to_parquet(os.path.join(out, "index.parquet"), index=False, compression="zstd")
    json.dump(dict(region=dict(name="New Zealand", districts=provs[0]["region"].get("districts")),
                   tiles=[t for p in provs for t in p["tiles"]], built=max(p["built"] for p in provs), commit=commits[0]),
              open(os.path.join(out, "provenance.json"), "w"), indent=1)
    runs = [json.load(open(os.path.join(d, "run.json"))) for d in dirs]
    run = dict(region="nz", parcels=len(df), tiles=len(built), shares=n, seconds_total=sum(r["seconds"] for r in runs),
               seconds_longest_share=max(r["seconds"] for r in runs),
               index_mb=round(os.path.getsize(os.path.join(out, "index.parquet")) / 1e6, 1), duplicate_ids=0,
               water_unknown=int(df.water_pct.isna().sum()) if "water_pct" in df else None,
               district_unknown=int(df.territorial_authority.isna().sum()) if "territorial_authority" in df else None)
    json.dump(run, open(os.path.join(out, "run.json"), "w"), indent=1)
    print(json.dumps(run))


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    merge(sys.argv[1], sys.argv[2], int(sys.argv[3]), json.load(open(os.path.join(here, "nz_tiles.json"))))
