"""The precomputed queries, per council (inverse_queries.py runs them; T-33, T-87)."""
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
         question="High or General Residential parcels of at least 800 m² (not stacked with another zone over 10% of the parcel), under 25% covered by 2021 buildings, "
                  "90th-percentile slope under 10°, outside every KCDC flood layer (the 2021 District Plan overlay and the newer modelled extents), and a wastewater manhole with a "
                  "recorded invert within 30 m that sits at least 1 m below the parcel's lowest ground (where manholes tie as nearest, the deepest invert counts). Title type and easement "
                  "count returned (cross-lease and unit titles complicate subdivision); freehold first.",
         sql=f"""SELECT unit_id, appellation, title_types, easements_n, area_m2, building_2021_m2, slope_p90_deg, zones,
                 ww_mh_id, ww_mh_dist_m, ww_head_ground_min_minus_invert_m {BASE} {TERRAIN}
                 AND (json_extract(zones,'$."High Density Residential Zone"')::DOUBLE >= 90
                      OR json_extract(zones,'$."General Residential Zone"')::DOUBLE >= 90)
                 AND zones_total_pct - greatest(coalesce(json_extract(zones,'$."High Density Residential Zone"')::DOUBLE, 0),
                                                coalesce(json_extract(zones,'$."General Residential Zone"')::DOUBLE, 0)) < 10
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
                  "condition grade 4 or 5 (grade 0 treated as not assessed). Where pipes tie as nearest, the worst grade "
                  "counts. Caution: KCDC records far more pipes as installed in 1979 and 1980 than in any other year, "
                  "so many 1979 dates may be placeholders.",
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

# Porirua City (T-87): no three waters (D-16), no recommended building levels, one LiDAR survey
PDP_FLOOD = ["pdp_flood_overland_flow", "pdp_flood_stream_corridor", "pdp_flood_inundation"]
PDP_COAST = ["pdp_coastal_erosion_current", "pdp_coastal_erosion_1m_slr", "pdp_coastal_inundation_current", "pdp_coastal_inundation_1m_slr"]
Q_PORIRUA = [
    dict(id="P1", name="Residential infill candidates",
         question="High or Medium Density Residential parcels of at least 800 m² (that zone over at least 90% of the parcel, no other "
                  "zone over 10%), under 25% covered by PCC's building footprints, 90th-percentile slope under 10°, outside every "
                  "District Plan 2025 flood and coastal hazard overlay. No sewer condition: Porirua's three waters are not used (D-16). "
                  "PCC's footprints are mostly undated and miss newer buildings, so check `unmapped_structure_m2`.",
         sql=f"""SELECT unit_id, appellation, area_m2, building_m2, unmapped_structure_m2, slope_p90_deg, zones {BASE} {TERRAIN}
                 AND (json_extract(zones,'$."High Density Residential Zone"')::DOUBLE >= 90
                      OR json_extract(zones,'$."Medium Density Residential Zone"')::DOUBLE >= 90)
                 AND zones_total_pct - greatest(coalesce(json_extract(zones,'$."High Density Residential Zone"')::DOUBLE, 0),
                                                coalesce(json_extract(zones,'$."Medium Density Residential Zone"')::DOUBLE, 0)) < 10
                 AND area_m2 >= 800 AND building_m2 < 0.25*area_m2 AND slope_p90_deg < 10
                 AND {" AND ".join(f"{c} IS NULL" for c in PDP_FLOOD + PDP_COAST)}
                 AND pcc_flood_unmapped IS NULL   -- where flooding is not mapped, "outside every flood overlay" means nothing
                 ORDER BY area_m2 DESC""",
         sources=["parcels", "zones", "pcc_buildings", "dem_2023", "dsm_2023", *PDP_FLOOD, *PDP_COAST, "pcc_flood_unmapped"]),
    dict(id="P2", name="Coastal hazard with 1 m sea-level rise",
         question="Parcels with buildings that the District Plan 2025 maps in coastal erosion or the 1-in-100-year storm surge "
                  "with 1 m sea-level rise (at least 1% of the parcel), but not in the current-day extents; not in the Plimmerton "
                  "Farm Zone, where the 2025 plan does not apply.",
         sql=f"""SELECT unit_id, appellation, area_m2, building_m2, pdp_coastal_erosion_1m_slr, pdp_coastal_inundation_1m_slr
                 {BASE} AND building_m2 > 0
                 AND (coalesce(json_extract(pdp_coastal_erosion_1m_slr, '$."Coastal erosion with 1 m sea-level rise"')::DOUBLE, 0) >= 1
                      OR coalesce(json_extract(pdp_coastal_inundation_1m_slr, '$."1-in-100-year storm surge with 1 m sea-level rise"')::DOUBLE, 0) >= 1)
                 AND pdp_coastal_erosion_current IS NULL AND pdp_coastal_inundation_current IS NULL
                 AND plan_1999_plimmerton_farm IS NULL   -- the 2025 plan does not apply there (thirteenth review)
                 ORDER BY area_m2 DESC""",
         sources=["parcels", "pcc_buildings", *PDP_COAST, "plan_1999_plimmerton_farm"]),
    dict(id="P3", name="Heritage, notable tree or significant natural area on the parcel",
         question="Parcels with a District Plan 2025 heritage item or notable tree point inside or on their boundary, or "
                  "overlapping a notable tree group, heritage setting, heritage item extent, historic heritage site or "
                  "significant natural area.",
         sql=f"""SELECT unit_id, appellation, area_m2, pdp_heritage_items, pdp_notable_trees, pdp_notable_tree_groups,
                        pdp_heritage_settings, pdp_heritage_item_extents, pdp_heritage_sites, pdp_significant_natural_areas
                 {BASE} AND (pdp_heritage_items <> '[]' OR pdp_notable_trees <> '[]' OR pdp_notable_tree_groups IS NOT NULL
                             OR pdp_heritage_settings IS NOT NULL OR pdp_heritage_item_extents IS NOT NULL
                             OR pdp_heritage_sites IS NOT NULL OR pdp_significant_natural_areas IS NOT NULL)""",
         sources=["parcels", "pdp_heritage_items", "pdp_notable_trees", "pdp_notable_tree_groups", "pdp_heritage_settings",
                  "pdp_heritage_item_extents", "pdp_heritage_sites", "pdp_significant_natural_areas"]),
]
