"""Region-wide inverse queries over a compiled block or the merged district (T-33, T-21).

Each query is a plain filter over raw primitives (no scores). Every returned row carries the parcel id and
appellation, the values it was selected on, and the provenance of each source those values came from: URL and licence once per query, and the
sha256 and fetch time of the data the row's own block was compiled from. Usage: inverse_queries.py DIR [DBFILE] (default DIR/tile.duckdb).
Output: DIR/inverse_queries.json and a markdown summary on stdout.
"""
import json, os, sys
import duckdb
from provenance import row_sources, source_summary

D = sys.argv[1] if len(sys.argv) > 1 else "data"
DBF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "tile.duckdb")
db = duckdb.connect(DBF, read_only=True)
PROV = {k: json.loads(v) for k, v in db.execute("SELECT source, json FROM provenance").fetchall()}
LIDAR_OFFSET_M = 0.08  # fallback only, for a block with too little flat open ground to measure its own offset

FLOOD_LAYERS = ["flood_river_corridor", "flood_stream_corridor", "flood_overflow_path", "flood_residual_overflow",
                "flood_fill_control", "flood_storage", "flood_ponding", "flood_residual_ponding", "flood_shallow_surface"]
NO_NEW_FLOOD = " AND ".join(f"{c} IS NULL" for c in FLOOD_LAYERS)

# Only parcels wholly inside the tile, so terrain and overlay values cover the whole parcel.
BASE = "FROM units WHERE coverage_pct >= 99 AND area_m2 >= 20"
# terrain-based queries also need LiDAR over the whole parcel (T-43)
TERRAIN = "AND lidar_coverage_pct >= 99"

Q = [
    dict(id="Q1", name="Gravity-serviceable infill candidates",
         question="High or General Residential parcels of at least 800 m², under 25% covered by 2021 buildings, "
                  "90th-percentile slope under 10°, outside every KCDC flood layer (the 2021 District Plan overlay and the newer modelled extents), and a wastewater manhole with a "
                  "recorded invert within 30 m that sits at least 1 m below the parcel's lowest ground. Title type and easement "
                  "count returned (cross-lease and unit titles complicate subdivision); freehold first.",
         sql=f"""SELECT unit_id, appellation, title_types, easements_n, area_m2, building_2021_m2, slope_p90_deg, zones,
                 ww_mh_id, ww_mh_dist_m, ww_head_ground_min_minus_invert_m {BASE} {TERRAIN}
                 AND (json_extract(zones,'$."High Density Residential Zone"')::DOUBLE >= 90
                      OR json_extract(zones,'$."General Residential Zone"')::DOUBLE >= 90)
                 AND area_m2 >= 800 AND building_2021_m2 < 0.25*area_m2 AND slope_p90_deg < 10
                 AND ovl_flood_hazard IS NULL AND {NO_NEW_FLOOD} AND ww_mh_dist_m <= 30 AND ww_head_ground_min_minus_invert_m >= 1
                 ORDER BY (title_types = 'Freehold') DESC, area_m2 DESC""",
         sources=["parcels", "titles", "nonprimary_parcels", "zones", "buildings_2021", "dem_2025", "ovl_flood_hazard", *FLOOD_LAYERS, "ww_node"]),
    dict(id="Q2", name="Recommended floor level well above ground",
         question="Built-on parcels where the highest KCDC recommended building level (a minimum floor level, "
                  "NZVD2016, including freeboard) inside the parcel is more than 1 m above the parcel's mean LiDAR "
                  "ground. A floor-height requirement for rebuilding, not a flood depth.",
         sql=f"""SELECT unit_id, appellation, building_2021_m2, ground_mean_m, rbl_in_parcel_n,
                 rbl_in_parcel_max_nzvd2016, rbl_in_parcel_max_minus_ground_mean_m, ovl_flood_hazard
                 {BASE} {TERRAIN} AND building_2021_m2 > 0 AND rbl_in_parcel_max_minus_ground_mean_m > 1
                 ORDER BY rbl_in_parcel_max_minus_ground_mean_m DESC""",
         sources=["parcels", "buildings_2021", "dem_2025", "flood_rbl_nzvd2016", "ovl_flood_hazard"]),
    dict(id="Q3", name="Nearest sewer is old and in poor condition",
         question="Parcels whose nearest wastewater pipe (within 20 m) was installed before 1980 and has KCDC "
                  "condition grade 4 or 5 (grade 0 treated as not assessed).",
         sql=f"""SELECT unit_id, appellation, ww_pipe_id, ww_pipe_dist_m, ww_pipe_material, ww_pipe_year,
                 ww_pipe_condition_grade {BASE} AND ww_pipe_dist_m <= 20 AND ww_pipe_year < 1980
                 AND ww_pipe_condition_grade >= 4 ORDER BY ww_pipe_condition_grade DESC, ww_pipe_year""",
         sources=["parcels", "ww_pipe"]),
    dict(id="Q4", name="Ground level changed since 2021",
         question="Parcels where some 1 m cell of LiDAR ground changed by more than 1 m between the 2021 and 2024–25 "
                  "surveys, and the parcel's mean ground changed by more than 0.3 m after removing its block's epoch "
                  "offset (the median change on flat, open, unbuilt ground in the block). Ground surfaces exclude "
                  "buildings, so this is mostly earthworks, but it may also be vegetation classed as ground or a "
                  "survey artefact (unverified, see T-29).",
         sql=f"""SELECT unit_id, appellation, area_m2, building_2021_m2, dz_2021_2025_mean_m,
                 coalesce(lidar_epoch_offset_block_m, {LIDAR_OFFSET_M}) AS epoch_offset_m,
                 round(dz_2021_2025_mean_m - coalesce(lidar_epoch_offset_block_m, {LIDAR_OFFSET_M}), 3) AS dz_mean_corrected_m,
                 dz_2021_2025_absmax_m
                 {BASE} {TERRAIN} AND dz_2021_2025_absmax_m > 1
                 AND abs(dz_2021_2025_mean_m - coalesce(lidar_epoch_offset_block_m, {LIDAR_OFFSET_M})) > 0.3
                 ORDER BY abs(dz_2021_2025_mean_m - coalesce(lidar_epoch_offset_block_m, {LIDAR_OFFSET_M})) DESC""",
         sources=["parcels", "dem_2025", "dem_2021", "buildings_2021"]),
    dict(id="Q5", name="Heritage, notable tree or ecological site on the parcel",
         question="Parcels with a KCDC heritage place or notable tree point inside or on their boundary (with the "
                  "feature id), or overlapping an ecological site.",
         sql=f"""SELECT unit_id, appellation, area_m2, ovl_heritage_places, ovl_notable_trees, ovl_ecological_sites
                 {BASE} AND (ovl_heritage_places <> '[]' OR ovl_notable_trees <> '[]' OR ovl_ecological_sites IS NOT NULL)""",
         sources=["parcels", "ovl_heritage_places", "ovl_notable_trees", "ovl_ecological_sites"]),
]

def prov(keys):
    return {k: source_summary(PROV[k]) for k in keys if k in PROV}

BLOCK_OF = dict(db.execute("SELECT unit_id, block_id FROM units").fetchall())

out = dict(database=os.path.basename(DBF), blocks=db.execute("SELECT count(DISTINCT block_id) FROM units").fetchone()[0], universe=db.execute(f"SELECT count(*) {BASE}").fetchone()[0],
           queries=[])
for q in Q:
    res = db.execute(q["sql"]); cols = [c[0] for c in res.description]
    rows = [dict(zip(cols, r)) for r in res.fetchall()]
    for r in rows:  # each row: the sha256 and fetch time of the data its own block was compiled from
        r["block_id"] = BLOCK_OF.get(r["unit_id"]); r["sources"] = row_sources(PROV, q["sources"], r["block_id"])
    out["queries"].append(dict(id=q["id"], name=q["name"], question=q["question"], sql=" ".join(q["sql"].split()),
                               count=len(rows), provenance=prov(q["sources"]), rows=rows))
    print(f"| {q['id']} | {q['name']} | {len(rows)} |")
json.dump(out, open(os.path.join(D, "inverse_queries.json"), "w"), indent=1, default=str)
missing = sum(1 for q, qq in zip(Q, out["queries"]) for r in qq["rows"] for k in q["sources"] if k in PROV and k not in r["sources"])
print("rows missing a source's sha256 or fetch time:", missing)
print("universe:", out["universe"], "parcels wholly in tile")
