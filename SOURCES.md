# Sources: licence and resolution register

Last checked: 2026-11-06. One row per source used by the pipeline ([`pipeline`](pipeline/)).
This is a working record, not legal advice. Keys match `provenance.json` and the `inverse_queries.json` provenance.

**Licence status:** ✅ licence stated for the dataset · ◐ covered by a portal-wide statement, but no licence on the dataset itself ·
❌ not cleared for resale.
**Fit for parcel:** ✅ values are meaningful for a single parcel · ⚠ usable with the caveat shown · ❌ area context only.

## Licence basis

- **LINZ** (parcels, titles, easements, LiDAR): CC BY 4.0. Attribution: "Sourced from the LINZ Data Service and licensed for
  reuse under CC BY 4.0", plus the producers named for each LiDAR survey. Owner names are under a separate personal-data
  licence and are not fetched.
- **Kāpiti Coast District Council (KCDC)**: the [KCDC open data portal](https://data-kcdc.opendata.arcgis.com/) states that
  KCDC GIS data that can be accessed online is licensed CC BY 4.0. 23 of the portal's 90 catalogued datasets also carry the
  licence on the dataset itself. The council's 2012 [map viewer terms](https://www.kapiticoast.govt.nz/media/4iojb5t0/kapiti_internet_map_viewer_terms_and_conditions.pdf)
  allow viewing only and reserve all other rights, but they cover the map viewer website. The portal statement is
  newer and covers the data. Attribution: "Kāpiti Coast District Council, CC BY 4.0".
- **Greater Wellington Regional Council (GWRC)**: GWRC states that its open data is CC BY 4.0 unless stated otherwise
  ([GWRC mapping information](https://archive.gw.govt.nz/environment/environmental-data-and-information/geographic-mapping-information/)).
  The two layers used carry "© GWRC" with no other terms.

## Register

| Key | Dataset (owner) | Licence | Updated | Fit for parcel | Notes |
| --- | --- | --- | --- | --- | --- |
| `parcels` | NZ Primary Parcels via KCDC Cadastral mirror (LINZ) | ✅ LINZ CC BY 4.0 | matches LINZ 6 Nov 2026 | ✅ | Omits railway parcels (D-11) and clips parcels at the district boundary (97 of 27,521 differ from LINZ area by more than 1 m²). `DCDB` parcels are legacy digitised boundaries: less accurate than surveyed ones |
| `linz_parcels` | NZ Primary Parcels, layer 50823 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Used to check the mirror |
| `titles` | NZ Property Titles, layer 50804 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Type and estate only; owner count, no names |
| `nonprimary_parcels` | NZ Non-Primary Parcels, layer 50782 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Easements and land covenants (existence and shape, not terms) |
| `dem_2025`, `dsm_2025` | Kāpiti Coast LiDAR 1 m DEM/DSM 2024–25 (LINZ, KCDC, Aerial Surveys) | ✅ CC BY 4.0 | 2024–25 flight | ✅ | 1 m cells. Does not cover Kapiti Island or the foothills: 544 parcels (2%) have no terrain values |
| `dem_2021` | Kāpiti Coast LiDAR 1 m DEM 2021 (LINZ, KCDC, AAM NZ) | ✅ CC BY 4.0 | 2021 flight | ✅ | +0.08 m offset against 2024–25 on flat ground |
| `district_flow` | New Zealand LiDAR 1 m DEM, read at 10 m, gaps from the Contour-Interpolated 8 m DEM (LINZ; Geographx for the 8 m) | ✅ CC BY 4.0 | national mosaic, surveys 2008–2026 | ⚠ | 10 m mosaic over the district and the Tararua catchments draining into it (1745000–1835000 E, 5440000–5510000 N), built once per run by `district_flow.py` |
| `buildings_2021` | Kapiti Coast Building Outlines 2021 (KCDC, by AAM) | ◐ | catalogue 18 May 2023 | ⚠ | As at 2021; misses newer buildings |
| `zones` | Operative District Plan 2021 – Zones (KCDC) | ◐ | 27 May 2024 | ✅ | Drawn on the cadastre |
| `ovl_flood_hazard` | ODP 2021 – Flood Hazards (KCDC) | ◐ | 13 Jul 2021 | ⚠ | Plan overlay; newer modelling is in the `flood_*` layers |
| `ovl_heritage_places`, `ovl_notable_trees` | ODP 2021 – Historic Heritage Places, Notable Trees (KCDC) | ◐ | 13 Jul 2021 | ✅ | Points |
| `ovl_ecological_sites`, `ovl_noise_corridor` | ODP 2021 – Ecological Sites, Noise Corridors (KCDC) | ◐ | 22 Nov 2024 | ✅ | |
| `ovl_coastal_env`, `ovl_fault_avoidance` | ODP 2021 – Coastal Environment, Fault Avoidance Areas (KCDC) | ◐ | 13 Jul 2021 | ✅ | |
| `flood_river_corridor`, `flood_overflow_path`, `flood_residual_overflow`, `flood_fill_control`, `flood_residual_ponding` | KCDC Latest Flood Hazards (KCDC) | ✅ CC BY 4.0 | 12 Jan 2021 | ✅ | Modelled extents |
| `flood_storage` | KCDC Latest Flood Hazards – Storage (KCDC) | ✅ CC BY 4.0 | 29 Sep 2022 | ✅ | |
| `flood_stream_corridor`, `flood_ponding`, `flood_shallow_surface` | Latest Flood Hazards service, layers 1, 6, 8 (KCDC) | ◐ | not catalogued | ✅ | Served from the same public service but not in the catalogue |
| `flood_rbl_nzvd2016` | KCDC Recommended Building Lines – NZVD2016 (KCDC) | ◐ (the Wellington 1953 version is ✅) | 24 Jun 2024 | ✅ | Dense points (12,284 in the tile). A minimum floor level including freeboard, not a flood depth |
| `ww_node`, `ww_pipe`, `ww_lateral` | KCDC Wastewater Points, Pipes, Laterals (KCDC) | ✅ CC BY 4.0 | 12 Jan 2021 | ⚠ | KCDC calls utility data schematic. Inverts on 67% of manholes, 17% of pipes. Condition grade 0 has no published definition |
| `sw_pipe`, `ws_pipe` | KCDC Stormwater Pipes, Water Service Pipes (KCDC) | ✅ CC BY 4.0 | 12 Jan 2021, 26 Aug 2021 | ⚠ | Schematic |
| `sw_point` | Services Open Data layer 4, stormwater points (KCDC) | ◐ | not catalogued | ⚠ | Schematic; 38% private assets |
| `wind_stainless` | KCDC Stainless Zone (KCDC) | ✅ CC BY 4.0 | 12 Jan 2021 | ⚠ | Coarse coastal band |
| `wind_very_high`, `tsunami_zones`, `earthworks` | KCDC Wind and Corrosion, Tsunami, Earthworks services (KCDC) | ◐ | not catalogued | ⚠ | No features in the test tile. Tsunami zones are evacuation zones, not inundation depths |
| `gw_liquefaction` | Earthquake Liquefaction Potential (GWRC, from GNS 2018) | ◐ (© GWRC, regional CC BY statement) | 2018 basis | ❌ | One 32 km² polygon from regional geology |
| `gw_eq_slope_failure` | Earthquake Slope Failure potential (GWRC, 1995 series) | ◐ (© GWRC) | 1995 basis | ⚠ | Regional susceptibility zones |

**Tally:** of the 23 rows above (37 source keys), 11 have a licence stated on the dataset (✅) and 12 rely on a portal-wide
statement (◐). None are known to be closed to commercial reuse. Before anything is sold, someone should ask KCDC and GWRC to confirm, in writing, that the
portal-wide statements cover the uncatalogued service layers (the owner makes that contact, not an agent).

## Compiled columns (per parcel, table `units`)

> **Known problems in the current results (T-39 review, 6 Nov 2026)**, being fixed in T-40 to T-44: until the next
> district rebuild (T-45), zone and overlay shares in the published results can exceed 100% and some carry older zone
> names or the layer name (fixed in the code by T-40), and query provenance lacks sha256 and fetch time (fixed by T-41); `upslope_area_max_m2` stops at the block's fetch
> window and `flow_path_m` is a count of 1 m cells (fixed by T-42, which adds `catchment_area_max_m2`); winter sun, horizon and sky view are measured on the tree canopy where
> there are trees (fixed by T-43); `wind_rel_height_m` is biased low near the sea (fixed by T-42); the platform estimate is given for parcels too small
> to hold one, and terrain values are given for parcels only partly covered by LiDAR (both fixed by T-43). The five newer KCDC flood layers and
> `earthworks` are compiled from T-40 on. See [the review](docs/findings/2026-11-06-fresh-eyes-review.md).

**Kind:** **published** = a value as the source publishes it · **derived** = calculated exactly from published data
(an overlap, a distance, a statistic of LiDAR cells) · **modelled** = an estimate from a model with stated simplifications.

| Columns | Kind | Meaning |
| --- | --- | --- |
| `unit_id`, `appellation`, `parcel_intent`, `survey_area_m2`, `titles` | published | LINZ parcel id and fields as published |
| `block_id` | derived | The block the parcel was compiled in: `xmin_ymin_size` (NZTM2000, metres) |
| `area_m2`, `coverage_pct` | derived | Polygon area; share of it inside the block's fetch window (overlays and terrain cover only that share; queries use parcels at 99% or more) |
| `lidar_cells`, `lidar_coverage_pct` | derived | 1 m LiDAR cells with ground values on the parcel, and their share of the parcel; 0 means outside the LiDAR surveys and terrain columns are empty. Below 100%, terrain values describe only the covered part; the terrain-based queries need at least 99% |
| `title_types`, `title_count` | published | Distinct LINZ title types on the parcel (for example Freehold, Cross lease) and number of title references |
| `easements_n`, `land_covenants_n` | derived | LINZ easement and covenant parcels overlapping it by more than 1 m² |
| `zones`, `ovl_*`, `flood_*` (polygon layers), `wind_*`, `tsunami_zones`, `earthworks`, `gw_*` | derived | JSON of class name → % of parcel area covered. Overlapping features of the same class count once; overlaps under 0.5 m² are ignored. Class field: `zones` the operative District Plan zone (`ePlan_Zone`; the layer's `PDP_ZONE` holds older names for some features); `ovl_flood_hazard` and `flood_*` the flood class (`ZONE`); `tsunami_zones` the evacuation zone; `ovl_fault_avoidance` fault name and certainty; `ovl_noise_corridor` the boundary id; `gw_liquefaction` and `gw_eq_slope_failure` their class. Layers without a class field (`ovl_coastal_env`, `wind_*`, `earthworks`) give the overlay's name. Before T-40 (6 Nov 2026) shares were summed across overlapping features and could exceed 100% |
| `ovl_heritage_places`, `ovl_notable_trees` | derived | JSON list of heritage or tree points within 1 m of the parcel |
| `ground_min_m`, `ground_mean_m`, `ground_max_m` | derived | 2024–25 LiDAR ground height over the parcel, metres NZVD2016 |
| `slope_p50_deg`, `slope_p90_deg` | derived | Median and 90th-percentile ground slope over the parcel's 1 m cells |
| `building_2021_m2`, `open_ground_m2`, `open_ground_slope_lt5_m2` | derived | Area under 2021 building outlines; the rest; the rest that slopes under 5° |
| `canopy_gt3m_open_pct` | derived | Share of open ground where the surface is more than 3 m above ground (trees or structures) |
| `open_ground_clear_pct` | derived | Share of open ground with nothing standing more than 0.5 m above it in the 2024–25 DSM (no tree, shrub, hedge, fence, vehicle or building newer than the 2021 outlines) |
| `dz_2021_2025_mean_m`, `dz_2021_2025_absmax_m` | derived | Ground change 2021 → 2024–25, mean and largest single cell; not offset-corrected (subtract about 0.07 m) |
| `ww_mh_*` | derived | Nearest in-use council wastewater manhole that has an invert: distance, id, invert (NZVD2016) |
| `ww_head_ground_min_minus_invert_m` | derived | Parcel's lowest ground minus that invert: a rough fall available for gravity drainage, before pipe cover and grade |
| `ww_pipe_*` | published / derived | Nearest in-use council wastewater pipe: distance (derived), id, material code, diameter, install year, condition grade (1 very good to 5 very poor; 0 treated as not graded) |
| `sw_mh_*`, `ws_pipe_*` | published / derived | Nearest in-use council stormwater point with an invert; nearest water supply pipe and its diameter |
| `rbl_in_parcel_n`, `rbl_in_parcel_max_nzvd2016`, `rbl_in_parcel_max_minus_ground_mean_m` | derived | Recommended building level points inside the parcel; highest; how far it sits above mean ground (a floor-height requirement) |
| `rbl_max_nzvd2016`, `ground_min_minus_rbl_m` | derived | Highest recommended building level within 10 m, and lowest ground minus it. Picks up upslope values; don't read it as flood depth |
| `winter_sun_hours_open_mean`, `winter_sun_open_ge3h_pct` | modelled | Hours of direct sun on the ground on 21 June (hourly samples, NZST) over the clear open ground (`open_ground_clear_pct`): the mean, and the share getting 3 hours or more. Ground under trees is not counted; empty if no open ground is clear. Before T-43 (7 Nov 2026) this measured sun on the surface, which on wooded ground is the canopy. Shadows from buildings, trees and terrain within 300 m in the 2024–25 DSM; farther ranges are not counted |
| `roof_pitch_p50_deg`, `roof_flat_m2`, `roof_north_m2` | derived | From the 2024–25 DSM inside 2021 building outlines: median pitch, area under 5°, area facing north (315°–45°) at 5° or more |
| `roof_solar_rel_pct` | modelled | Clear-sky direct sun on the roof surface (shaded as above) over three representative days (21 June, 20 March, 21 December), as % of an unshaded horizontal surface at the same place. No cloud or diffuse light; compare roofs with each other, not with kWh figures |
| `upslope_area_max_m2`, `upslope_area_truncated`, `flow_path_m` | modelled | Overland flow on the 2024–25 1 m DEM (D8; depressions and flats drained by priority-flood, `flow.py`) within the block's LiDAR window: largest upslope area draining through the parcel; whether that upslope area reaches the window edge or a LiDAR gap over land, so may be larger (true for river corridors: use `catchment_area_max_m2`); and length in metres of flow paths across the parcel draining at least 2,000 m². Ignores stormwater pipes, culverts and bridges, so urban flows are overstated |
| `catchment_area_max_m2`, `catchment_truncated` | modelled | Largest upslope area draining through the parcel on the 10 m district mosaic (`district_flow`), so whole river catchments are counted, and whether it reaches the mosaic edge. Embankments without their culverts can divert flow: on the plain north of Ōtaki the Waitohu shows about 130 km² because flow is routed north across it. Checked: Waikanae 148 km² and Ōtaki 374 km² near their mouths |
| `level_open_cut_m3`, `level_open_fill_m3` | derived | Cut and fill to bring all open ground to its median level |
| `platform_15m_earthworks_min_m3` | modelled | Smallest earthworks for a 15 m × 15 m level platform lying wholly on the parcel's open ground, estimated from the spread of ground levels; empty where no such square fits |
| `wind_obstruction_pct`, `wind_rel_height_m` | derived | Share of the surrounding ±100 m (square) with obstructions over 2.5 m in the DSM; ground at the parcel (1 m DEM) relative to the mean ground within ±500 m on the 10 m district mosaic, with the sea at 0 m. Inputs to wind exposure, not an exposure rating: a modelled exposure class built from these two disagreed with KCDC's wind zones (T-37) and is withheld |
| `horizon_mean_deg`, `horizon_north_deg`, `sky_view_pct` | derived | From the most open spot on the section at 1.6 m eye height (the clear open-ground cell farthest from buildings, trees and the boundary; empty if no open ground is clear): mean horizon angle in 16 directions, the highest towards north (N, NNE, NNW), and sky view (100 = open sky) |
