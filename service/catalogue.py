"""Column and source catalogue for the query service (T-36).

`SOURCES.md` is the single record of each source's licence and fit for parcel use, and of each column's kind and
meaning; this module reads them from it. The one thing added here is which sources each column is computed from
(COLUMN_SOURCES). Tests check that every compiled column is covered and every source key is in the register.
"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LICENCE = {"✅": "dataset licence", "◐": "portal-wide statement, to be confirmed in writing (T-35)"}
FIT = {"✅": "fit", "⚠": "use with caution", "❌": "not fit for parcel use", "—": "not applicable"}
FIT_RANK = {"fit": 0, "not applicable": 0, "use with caution": 1, "not fit for parcel use": 2, "unknown": 3}

# Columns never served in public mode whatever their licence (D-12: facts about land, never people)
PUBLIC_EXCLUDE = {"titles": "title references are a direct key to owner records; the title count is served instead (T-55)",
                  "title_types": "a title type such as Life Estate can describe a living person's interest (T-67, D-17)"}

# Which sources each column is computed from, first match wins. Every derived value also depends on the parcel.
P = ["parcels"]
COLUMN_SOURCES = [
    (r"(unit_id|appellation|parcel_intent|survey_area_m2|titles|geometry_source|unit_source|area_m2|coverage_pct|rep_[xy]|bbox_\w+)", P),
    (r"block_id", []),
    (r"district_share_pct", P + ["district_outline"]),
    (r"title_count", P),  # counted from the parcel's own titles field
    (r"title_types", P + ["titles"]),
    (r"easements_n|land_covenants_n", P + ["nonprimary_parcels"]),
    (r"zones_total_pct", P + ["zones"]),
    # read at the viewpoint, which is chosen on open ground outside the 2021 building outlines (T-52)
    (r"wind_obstruction_pct", P + ["dem_2025", "dsm_2025", "buildings_2021"]),
    (r"wind_rel_height_m", P + ["dem_2025", "dsm_2025", "buildings_2021", "district_flow"]),
    (r"ground_min_minus_rbl_m|rbl_in_parcel_max_minus_ground_mean_m", P + ["flood_rbl_nzvd2016", "dem_2025"]),
    (r"rbl_\w+", P + ["flood_rbl_nzvd2016"]),
    (r"ww_head_ground_min_minus_invert_m", P + ["ww_node", "dem_2025", "sea_mask"]),
    (r"ww_mh_\w+", P + ["ww_node"]),
    (r"ww_pipe_\w+", P + ["ww_pipe"]),
    (r"sw_mh_\w+", P + ["sw_point"]),
    (r"ws_pipe_\w+", P + ["ws_pipe"]),
    (r"catchment_\w+", P + ["district_flow"]),
    (r"(zones|ovl_\w+|flood_\w+|wind_\w+|tsunami_zones|earthworks|gw_\w+)", None),  # an overlay: its own source key
    # the district grid masks the sea for coverage, and gives the flow its outlets and edge inflow (T-52)
    (r"lidar_coverage_pct|upslope_area_\w+|flow_path_m", P + ["dem_2025", "district_flow"]),
    (r"lidar_cells|ground_(min|mean|max)_m|slope_p\d+_deg", P + ["dem_2025", "sea_mask"]),  # sea cells removed (T-59)
    (r"dz_2021_2025_clear_\w+", P + ["dem_2025", "dem_2021", "dsm_2025", "sea_mask"]),
    (r"dz_2021_2025_\w+", P + ["dem_2025", "dem_2021", "sea_mask"]),
    (r"lidar_epoch_offset_block_m", ["dem_2025", "dem_2021", "dsm_2025"]),  # LiDAR only since T-54
    (r"buildings_coverage_pct", P + ["buildings_capture_area", "district_outline"]),
    (r"unmapped_structure_m2", P + ["dem_2025", "dsm_2025", "buildings_2021"]),
    (r"building_2021_m2|open_ground_m2|open_ground_slope_lt5_m2|level_open_\w+|platform_15m_earthworks_min_m3", P + ["dem_2025", "buildings_2021"]),
    (r"canopy_gt3m_open_pct|open_ground_clear_pct|winter_sun_\w+|horizon_\w+|sky_view_pct", P + ["dem_2025", "dsm_2025", "buildings_2021"]),
    (r"roof_\w+", P + ["dsm_2025", "buildings_2021"]),
]


def _table(text, heading, header_in_heading=False):
    """Rows of the first markdown table after `heading`, as lists of cell strings."""
    i = text.index(heading)
    rows = []
    for line in text[i:].splitlines()[1:]:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("- "): rows.append(cells)
        elif rows: break
    return rows if header_in_heading else rows[1:]  # without the header row


def _symbol(cell, table):
    for k in table:
        if cell.startswith(k): return table[k]
    return None


def load(path=os.path.join(ROOT, "SOURCES.md")):
    text = open(path, encoding="utf-8").read()
    sources = {}
    for key_cell, dataset, lic, updated, fit, notes in (r[:6] for r in _table(text, "## Register")):
        for k in re.findall(r"`([^`]+)`", key_cell):
            sources[k] = dict(dataset=dataset, licence=lic, licence_status=_symbol(lic, LICENCE) or "unknown",
                              licence_cleared=lic.startswith("✅"), fit=_symbol(fit, FIT) or "unknown", updated=updated, notes=notes)
    exact, globs = [], []
    for cols, kind, meaning in (r[:3] for r in _table(text, "| Columns | Kind | Meaning |", header_in_heading=True)):
        for pat in re.findall(r"`([^`]+)`", cols):
            entry = (re.compile("^" + re.escape(pat).replace(r"\*", r"\w+") + "$"), kind, meaning)
            (globs if "*" in pat else exact).append(entry)
    return sources, exact + globs  # a column's own row wins over a pattern such as `wind_*` (T-52)


SOURCES, _COLUMNS = load()


LIDAR = {"dem_2025", "dsm_2025", "dem_2021"}


def column_sources(col):
    for pat, src in COLUMN_SOURCES:
        if re.fullmatch(pat, col):
            out = [col] + P if src is None else list(src)
            # every LiDAR surface is masked by the district grid's sea before use (T-59, T-62)
            if LIDAR & set(out) and "sea_mask" not in out: out.append("sea_mask")
            return out
    return None


def column_meta(col):
    """Kind, meaning, sources, the weakest fit-for-parcel flag of its sources, and whether every source is licence-cleared."""
    kind = meaning = None
    for pat, k, m in _COLUMNS:
        if pat.match(col): kind, meaning = k, m; break
    src = column_sources(col)
    if src is None or kind is None: return None
    s = [SOURCES.get(k) for k in src]
    fit = max((x["fit"] if x else "unknown" for x in s), key=lambda f: FIT_RANK.get(f, 3), default="not applicable")
    return dict(kind=kind, meaning=meaning, sources=src, fit=fit,
                licence_cleared=all(x and x["licence_cleared"] for x in s))
