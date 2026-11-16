"""District-level checks of computed measures against independent council layers (T-37).

Usage: check_measures.py DBFILE OUTJSON. Each check reports how much more often a modelled measure flags parcels
that an independent KCDC layer also flags, compared with all parcels (the lift). A lift near 1 means no agreement.
"""
import json, sys
import duckdb

db = duckdb.connect(sys.argv[1], read_only=True)
BASE = "FROM units WHERE coverage_pct >= 99 AND area_m2 >= 20 AND lidar_cells > 0"
# which parcels every check counts, written into the results so a reader knows (T-95)
UNIVERSE = ("parcels whose fetch window covers at least 99% of them, of 20 m² or more, with LiDAR cells: a lift compares "
            "the share of flagged parcels in the reference layer with the share of all of these")

def lift(flag, ref):
    n, nf, nr, nfr = db.execute(f"SELECT count(*), count(*) FILTER (WHERE {flag}), count(*) FILTER (WHERE {ref}), "
                                f"count(*) FILTER (WHERE ({flag}) AND ({ref})) {BASE}").fetchone()
    return dict(parcels=n, flagged=nf, in_reference=nr, both=nfr,
                share_of_flagged_in_reference=round(nfr / nf, 3) if nf else None,
                share_of_all_in_reference=round(nr / n, 3) if n else None,
                lift=round((nfr / nf) / (nr / n), 2) if nf and nr else None)

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from councils import COUNCIL
if COUNCIL.NAME == "porirua":   # PCC's own layers (T-87)
    json.dump(dict(universe=UNIVERSE, overland_flow_path_vs_pcc_flood_overlays=lift("flow_path_m > 0", "(pdp_flood_overland_flow IS NOT NULL "
              "OR pdp_flood_stream_corridor IS NOT NULL OR pdp_flood_inundation IS NOT NULL)")), open(sys.argv[2], "w"), indent=1)
    sys.exit(0)
flood = ("(ovl_flood_hazard IS NOT NULL OR flood_stream_corridor IS NOT NULL OR flood_overflow_path IS NOT NULL "
         "OR flood_storage IS NOT NULL OR flood_ponding IS NOT NULL)")
out = dict(
    universe=UNIVERSE,
    overland_flow_path_vs_kcdc_flood_hazard=lift("flow_path_m > 0", flood),
    # the modelled wind class failed this check (lift 0.58 and 0.31 on the densest block) and was withdrawn; the
    # input is still reported so a better model can be compared later
    low_obstruction_vs_kcdc_very_high_wind_zone=lift("wind_obstruction_pct < 10", "wind_very_high IS NOT NULL"),
    low_obstruction_vs_kcdc_coastal_stainless_zone=lift("wind_obstruction_pct < 10", "wind_stainless IS NOT NULL"),
    high_floor_level_vs_overland_flow=lift("rbl_in_parcel_max_minus_ground_mean_m > 1", "flow_path_m > 0"),
)
json.dump(out, open(sys.argv[2], "w"), indent=1)
for k, v in out.items():
    if isinstance(v, dict): print(f"{k}: lift {v['lift']} ({v['both']} of {v['flagged']} flagged)")
