"""Merge compiled blocks into one district database (T-21).

Usage: merge_blocks.py BLOCKS_DIR OUT_DIR. BLOCKS_DIR holds one folder per block, each with units.parquet,
provenance.json, qa.json and fetch_bbox.json. Writes OUT_DIR/district.duckdb (tables units, provenance, blocks),
OUT_DIR/units.parquet, OUT_DIR/blocks.json and OUT_DIR/qa_summary.json.
"""
import glob, json, os, sys
import duckdb

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
dirs = sorted(d for d in glob.glob(os.path.join(SRC, "*")) if os.path.exists(os.path.join(d, "units.parquet")))
blocks, prov = [], {}
for d in dirs:
    p = json.load(open(os.path.join(d, "provenance.json")))
    qa = json.load(open(os.path.join(d, "qa.json"))) if os.path.exists(os.path.join(d, "qa.json")) else {}
    failed = [k for k, v in p["sources"].items() if not v.get("ok", True) and not v.get("no_coverage")]
    no_cov = [k for k, v in p["sources"].items() if v.get("no_coverage")]
    blocks.append(dict(block=p.get("block"), fetch_bbox=p.get("fetch_bbox"), parcels=p["sources"].get("parcels", {}).get("features"),
                       failed_sources=failed, no_coverage=no_cov, qa=qa))
    for k, v in p["sources"].items():
        e = prov.setdefault(k, dict(url=v.get("url") or v.get("collection"), licence=v.get("licence"), blocks=0, failed_blocks=0,
                                    features=0, fetched_first=None, fetched_last=None, sha256_by_block={}))
        e["blocks"] += 1; e["failed_blocks"] += 0 if v.get("ok", True) else 1
        e["features"] += v.get("features") or 0
        t = p.get("fetched_at") or v.get("fetched")
        if t: e["fetched_first"] = min(filter(None, [e["fetched_first"], t])); e["fetched_last"] = max(filter(None, [e["fetched_last"], t]))
        if v.get("sha256"): e["sha256_by_block"]["_".join(map(str, p.get("block") or []))] = v["sha256"]

db = duckdb.connect(os.path.join(OUT, "district.duckdb"))
files = [os.path.join(d, "units.parquet") for d in dirs]
db.execute(f"CREATE OR REPLACE TABLE all_units AS SELECT * FROM read_parquet({files!r}, union_by_name=true)")
# a parcel whose representative point lies exactly on a block edge can appear twice: keep the fuller copy
db.execute("""CREATE OR REPLACE TABLE units AS SELECT * EXCLUDE (rn) FROM (
              SELECT *, row_number() OVER (PARTITION BY unit_id ORDER BY coverage_pct DESC, block_id) AS rn FROM all_units) WHERE rn = 1""")
dups = db.execute("SELECT count(*) - count(DISTINCT unit_id) FROM all_units").fetchone()[0]
db.execute("DROP TABLE all_units")
db.execute("CREATE OR REPLACE TABLE provenance (source VARCHAR, json VARCHAR)")
db.executemany("INSERT INTO provenance VALUES (?, ?)", [(k, json.dumps(v)) for k, v in prov.items()])
db.execute(f"COPY units TO '{os.path.join(OUT, 'units.parquet')}' (FORMAT PARQUET)")
json.dump(blocks, open(os.path.join(OUT, "blocks.json"), "w"), indent=1)

def pooled(key):
    xs = [b["qa"].get(key, {}) for b in blocks if b["qa"].get(key, {}).get("n")]
    n = sum(x["n"] for x in xs)
    return dict(n=n, blocks=len(xs), median_of_block_medians=sorted(x["median"] for x in xs)[len(xs) // 2] if xs else None,
                worst_block_median=max((x["median"] for x in xs), key=abs) if xs else None)
n, nl, part = db.execute("SELECT count(*), count(*) FILTER (WHERE lidar_cells = 0), count(*) FILTER (WHERE coverage_pct < 99) FROM units").fetchone()
qs = dict(blocks=len(blocks), blocks_with_failed_sources=sum(1 for b in blocks if b["failed_sources"]),
          blocks_outside_lidar=sum(1 for b in blocks if b["no_coverage"]), parcels=n,
          duplicates_removed=dups, parcels_without_lidar=nl, parcels_partly_outside_window=part,
          manhole_cover_minus_lidar_m=pooled("manhole_cover_minus_lidar_m"),
          building_ground_minus_lidar_m=pooled("building_ground_minus_lidar_m"),
          lidar_2025_minus_2021_flat_m=pooled("lidar_2025_minus_2021_flat_m"),
          roof_dsm_minus_kcdc_bld_ave_m=pooled("roof_dsm_minus_kcdc_bld_ave_m"),
          parcel_area_max_abs_diff_m2=max((b["qa"].get("parcel_area_minus_linz_calc_m2", {}).get("max_abs") or 0) for b in blocks) if blocks else None)
json.dump(qs, open(os.path.join(OUT, "qa_summary.json"), "w"), indent=1)
print(json.dumps(qs, indent=1))
