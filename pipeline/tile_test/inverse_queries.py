"""Region-wide inverse queries over the compiled tile (T-33).

Each query is a plain filter over raw primitives (no scores). Every returned row carries the parcel id and
appellation, the values it was selected on, and the provenance (URL, sha256, fetch time, licence) of each
source those values came from. Output: data/inverse_queries.json and a markdown summary on stdout.
"""
import json, os, sys
import duckdb

D = sys.argv[1] if len(sys.argv) > 1 else "data"
db = duckdb.connect(os.path.join(D, "tile.duckdb"), read_only=True)
PROV = {k: json.loads(v) for k, v in db.execute("SELECT source, json FROM provenance").fetchall()}
LIDAR_OFFSET_M = 0.08  # systematic 2024-25 minus 2021 offset on flat ground (findings, 6 Nov 2026)

# Only parcels wholly inside the tile, so terrain and overlay values cover the whole parcel.
BASE = "FROM units WHERE in_tile_pct >= 99 AND area_m2 >= 20"

Q = [
    dict(id="Q1", name="Gravity-serviceable infill candidates",
         question="High or General Residential parcels of at least 800 m², under 25% covered by 2021 buildings, "
                  "90th-percentile slope under 10°, no KCDC flood hazard overlay, and a wastewater manhole with a "
                  "recorded invert within 30 m that sits at least 1 m below the parcel's lowest ground. Title type and easement "
                  "count returned (cross-lease and unit titles complicate subdivision); freehold first.",
         sql=f"""SELECT unit_id, appellation, title_types, easements_n, area_m2, building_2021_m2, slope_p90_deg, zones,
                 ww_mh_id, ww_mh_dist_m, ww_head_ground_min_minus_invert_m {BASE}
                 AND (json_extract(zones,'$."High Density Residential Zone"')::DOUBLE >= 90
                      OR json_extract(zones,'$."General Residential Zone"')::DOUBLE >= 90)
                 AND area_m2 >= 800 AND building_2021_m2 < 0.25*area_m2 AND slope_p90_deg < 10
                 AND ovl_flood_hazard IS NULL AND ww_mh_dist_m <= 30 AND ww_head_ground_min_minus_invert_m >= 1
                 ORDER BY (title_types = 'Freehold') DESC, area_m2 DESC""",
         sources=["parcels", "titles", "nonprimary_parcels", "zones", "buildings_2021", "dem_2025", "ovl_flood_hazard", "ww_node"]),
    dict(id="Q2", name="Recommended floor level well above ground",
         question="Built-on parcels where the highest KCDC recommended building level (a minimum floor level, "
                  "NZVD2016, including freeboard) inside the parcel is more than 1 m above the parcel's mean LiDAR "
                  "ground. A floor-height requirement for rebuilding, not a flood depth.",
         sql=f"""SELECT unit_id, appellation, building_2021_m2, ground_mean_m, rbl_in_parcel_n,
                 rbl_in_parcel_max_nzvd2016, rbl_in_parcel_max_minus_ground_mean_m, ovl_flood_hazard
                 {BASE} AND building_2021_m2 > 0 AND rbl_in_parcel_max_minus_ground_mean_m > 1
                 ORDER BY rbl_in_parcel_max_minus_ground_mean_m DESC""",
         sources=["parcels", "buildings_2021", "dem_2025", "flood_rbl_nzvd2016", "ovl_flood_hazard"]),
    dict(id="Q3", name="Nearest sewer is old and in poor condition",
         question="Parcels whose nearest wastewater pipe (within 20 m) was installed before 1980 and has KCDC "
                  "condition grade 4 or 5 (grade 0 treated as not assessed).",
         sql=f"""SELECT unit_id, appellation, ww_pipe_id, ww_pipe_dist_m, ww_pipe_material, ww_pipe_year,
                 ww_pipe_condition_grade {BASE} AND ww_pipe_dist_m <= 20 AND ww_pipe_year < 1980
                 AND ww_pipe_condition_grade >= 4 ORDER BY ww_pipe_condition_grade DESC, ww_pipe_year""",
         sources=["parcels", "ww_pipe"]),
    dict(id="Q4", name="Ground change since 2021 not explained by buildings",
         question=f"Parcels where some 1 m cell changed by more than 1 m between the 2021 and 2024–25 LiDAR and the "
                  f"parcel mean changed by more than 0.3 m after removing the {LIDAR_OFFSET_M} m epoch offset. "
                  "Unverified: may be earthworks, new buildings, or vegetation classed as ground (see T-29).",
         sql=f"""SELECT unit_id, appellation, area_m2, building_2021_m2, dz_2021_2025_mean_m,
                 round(dz_2021_2025_mean_m - {LIDAR_OFFSET_M}, 3) AS dz_mean_corrected_m, dz_2021_2025_absmax_m
                 {BASE} AND dz_2021_2025_absmax_m > 1 AND abs(dz_2021_2025_mean_m - {LIDAR_OFFSET_M}) > 0.3
                 ORDER BY abs(dz_2021_2025_mean_m - {LIDAR_OFFSET_M}) DESC""",
         sources=["parcels", "dem_2025", "dem_2021", "buildings_2021"]),
    dict(id="Q5", name="Heritage, notable tree or ecological site on the parcel",
         question="Parcels containing a KCDC heritage place or notable tree point, or overlapping an ecological site.",
         sql=f"""SELECT unit_id, appellation, area_m2, ovl_heritage_places, ovl_notable_trees, ovl_ecological_sites
                 {BASE} AND (ovl_heritage_places <> '[]' OR ovl_notable_trees <> '[]' OR ovl_ecological_sites IS NOT NULL)""",
         sources=["parcels", "ovl_heritage_places", "ovl_notable_trees", "ovl_ecological_sites"]),
]

def prov(keys):
    return {k: {f: PROV[k].get(f) for f in ("url", "sha256", "fetched", "licence", "features")} for k in keys if k in PROV}

out = dict(tile=[1769000, 5468400, 1770000, 5469400], universe=db.execute(f"SELECT count(*) {BASE}").fetchone()[0],
           queries=[])
for q in Q:
    res = db.execute(q["sql"]); cols = [c[0] for c in res.description]
    rows = [dict(zip(cols, r)) for r in res.fetchall()]
    out["queries"].append(dict(id=q["id"], name=q["name"], question=q["question"], sql=" ".join(q["sql"].split()),
                               count=len(rows), provenance=prov(q["sources"]), rows=rows))
    print(f"| {q['id']} | {q['name']} | {len(rows)} |")
json.dump(out, open(os.path.join(D, "inverse_queries.json"), "w"), indent=1, default=str)
print("universe:", out["universe"], "parcels wholly in tile")
