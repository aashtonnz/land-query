# Sources: licence and resolution register

Last checked: 2026-11-06. One row per source used by the live tile pipeline ([`pipeline`](pipeline/)).
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
| `parcels` | NZ Primary Parcels via KCDC Cadastral mirror (LINZ) | ✅ LINZ CC BY 4.0 | matches LINZ 6 Nov 2026 | ✅ | Omits railway parcels (D-11). `DCDB` parcels are legacy digitised boundaries: less accurate than surveyed ones |
| `linz_parcels` | NZ Primary Parcels, layer 50823 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Used to check the mirror |
| `titles` | NZ Property Titles, layer 50804 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Type and estate only; owner count, no names |
| `nonprimary_parcels` | NZ Non-Primary Parcels, layer 50782 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Easements and land covenants (existence and shape, not terms) |
| `dem_2025`, `dsm_2025` | Kāpiti Coast LiDAR 1 m DEM/DSM 2024–25 (LINZ, KCDC, Aerial Surveys) | ✅ CC BY 4.0 | 2024–25 flight | ✅ | 1 m cells |
| `dem_2021` | Kāpiti Coast LiDAR 1 m DEM 2021 (LINZ, KCDC, AAM NZ) | ✅ CC BY 4.0 | 2021 flight | ✅ | +0.08 m offset against 2024–25 on flat ground |
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

## Compiled columns (per parcel, `tile.duckdb` table `units`)

| Columns | Meaning |
| --- | --- |
| `unit_id`, `appellation`, `parcel_intent`, `survey_area_m2`, `titles` | LINZ parcel id and fields as published |
| `area_m2`, `in_tile_pct` | Polygon area; share of it inside the tile (queries use only parcels at 99% or more) |
| `title_types`, `title_count` | Distinct LINZ title types on the parcel (for example Freehold, Cross lease) and number of title references |
| `easements_n`, `land_covenants_n` | Count of LINZ non-primary easement and covenant parcels overlapping it by more than 1 m² |
| `zones`, `ovl_*`, `flood_*` (polygon layers), `wind_*`, `tsunami_zones`, `gw_*` | JSON of class name → % of parcel area covered (overlaps under 0.5 m² ignored) |
| `ovl_heritage_places`, `ovl_notable_trees` | JSON list of heritage or tree points within 1 m of the parcel |
| `ground_min_m`, `ground_mean_m`, `ground_max_m` | 2024–25 LiDAR ground height over the parcel, metres NZVD2016 |
| `slope_p50_deg`, `slope_p90_deg` | Median and 90th-percentile ground slope over the parcel's 1 m cells |
| `building_2021_m2`, `open_ground_m2`, `open_ground_slope_lt5_m2` | Area under 2021 building outlines; the rest; the rest that slopes under 5° |
| `canopy_gt3m_open_pct` | Share of open ground where surface is more than 3 m above ground (trees or structures) |
| `dz_2021_2025_mean_m`, `dz_2021_2025_absmax_m` | Ground change 2021 → 2024–25, mean and largest single cell; not offset-corrected |
| `ww_mh_*` | Nearest in-use council wastewater manhole that has an invert: distance, id, invert (NZVD2016) |
| `ww_head_ground_min_minus_invert_m` | Parcel's lowest ground minus that invert: a rough fall available for gravity drainage, before pipe cover and grade |
| `ww_pipe_*` | Nearest in-use council wastewater pipe: distance, id, material code, diameter, install year, condition grade (1 very good to 5 very poor; 0 treated as not graded) |
| `sw_mh_*`, `ws_pipe_*` | Nearest in-use council stormwater point with an invert; nearest water supply pipe and its diameter |
| `rbl_in_parcel_n`, `rbl_in_parcel_max_nzvd2016`, `rbl_in_parcel_max_minus_ground_mean_m` | Recommended building level points inside the parcel; highest; how far it sits above mean ground (a floor-height requirement) |
| `rbl_max_nzvd2016`, `ground_min_minus_rbl_m` | Highest recommended building level within 10 m, and lowest ground minus it. Picks up upslope values, so don't read it as flood depth |
