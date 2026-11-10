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
| `parcels` | NZ Primary Parcels, layer 50823 (LINZ), by parcel id; district and block membership from the KCDC Cadastral mirror, kept where the parcel's representative point, or at least 1,000 m² of it, lies inside the district (`district_outline`; T-65, T-70). Whole parcels are published (T-69): a few reach far outside the district (Section 5 SO 495075 is 615 km², about 40 km² of it inside) | ✅ LINZ CC BY 4.0 | weekly | ✅ | Geometry and fields from LINZ since D-13 (7 Nov 2026). The mirror omits railway parcels (D-11), is not clipped to the district (it holds parcels in Porirua, Horowhenua and Upper Hutt, which are dropped: T-62, T-65), and truncates some parcels lying inside the district (39 in block 1785000_5485000; for example Lot 1 DP 70514 is 7,463 m² in the mirror and 4.43 km² in LINZ). `geometry_source` says which a parcel uses; without the LINZ key, the mirror is used for every parcel |
| `kcdc_parcels` | KCDC Cadastral mirror of NZ Primary Parcels (KCDC) | ✅ LINZ CC BY 4.0 | matches LINZ for most parcels | — | QA cross-check only (D-13) |
| `district_boundary` | Cadastral service layer 1, District Boundary (KCDC) | ◐ | not catalogued | — | QA: parcels clipped at the boundary |
| `district_outline` | Three boundaries: KCDC's District Boundary line (Cadastral layer 1) closed at sea, the Kapiti Coast Māori Ward polygon (Comm_Board_Ward_Boundaries_2025 layer 1, the whole district), and Stats NZ's district polygon (GWRC Region_basemap_P layer 1, © Statistics NZ, CC BY 4.0) | ◐ | not catalogued | — | Decides which mirror parcels are in the district and gives `district_share_pct` (T-62, T-65, T-70). Land counts where at least two of the three agree; the sea and islands come from the line's sea loop. Each of the three disagrees with the others in slivers up to 6 ha |
| `titles` | NZ Property Titles, layer 50804 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Type and estate only; owner count, no names |
| `nonprimary_parcels` | NZ Non-Primary Parcels, layer 50782 (LINZ) | ✅ CC BY 4.0 | weekly | ✅ | Easements and land covenants (existence and shape, not terms) |
| `dem_2025`, `dsm_2025` | Kāpiti Coast LiDAR 1 m DEM/DSM 2024–25 (LINZ, KCDC, Aerial Surveys) | ✅ CC BY 4.0 | 2024–25 flight | ✅ | 1 m cells. Does not cover Kapiti Island or the foothills: 450 parcels (2%) in the 8 Nov 2026 results have no terrain values |
| `dem_2021` | Kāpiti Coast LiDAR 1 m DEM 2021 (LINZ, KCDC, AAM NZ) | ✅ CC BY 4.0 | 2021 flight | ✅ | +0.08 m offset against 2024–25 on flat ground |
| `district_flow` | New Zealand LiDAR 1 m DEM, read at 10 m, gaps from the Contour-Interpolated 8 m DEM (LINZ; Geographx for the 8 m) | ✅ CC BY 4.0 | national mosaic, surveys 2008–2026 | ⚠ | 10 m mosaic over the district and the Tararua catchments draining into it (1745000–1835000 E, 5440000–5510000 N), built once per run by `district_flow.py` |
| `sea_mask` | Sea cells from the `district_flow` grid: no value in LINZ's 8 m contour DEM and no higher than 0.5 m, extended along the shoreline at the 1 m survey's flat sea value (LINZ) | ✅ CC BY 4.0 | as `district_flow` | ✅ | Removes the sea from the 1 m LiDAR before ground levels, slope and ground change are computed; provenance is the `district_flow` record |
| `buildings_2021` | Kapiti Coast Building Outlines 2021 (KCDC, by AAM) | ◐ | catalogue 18 May 2023 | ⚠ | As at 2021; misses newer buildings. Captured only inside the footprint of LINZ's 2017 urban aerial photos (`buildings_capture_area`; 50,621 of 50,623 outlines) and the district: none at Waiorua Bay on Kapiti Island, Reikorangi, the hills, or outside the district |
| `buildings_capture_area` | Capture area of LINZ's Kāpiti Coast 0.1 m urban aerial photos, 2017 (nz-imagery bucket) | ✅ LINZ CC BY 4.0 | 2017 | ⚠ | The area the 2021 building outlines cover (50,621 of 50,623 lie inside it; most were drawn from 0.3 m photos of 2017 and 2021). Inside it the outlines still miss some houses; `unmapped_structure_m2` warns of most of them (T-76, T-81) |
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
| `sw_point` | Services Open Data layer 4, stormwater points (KCDC) | ◐ | not catalogued | ⚠ | Schematic; 38% private assets. Only status `INUS` is used, which excludes private (`PRV`), NZTA, rail and GWRC assets |
| `wind_stainless` | KCDC Stainless Zone (KCDC) | ✅ CC BY 4.0 | 12 Jan 2021 | ⚠ | Coarse coastal band |
| `wind_very_high`, `tsunami_zones`, `earthworks` | KCDC Wind and Corrosion, Tsunami, Earthworks services (KCDC) | ◐ | not catalogued | ⚠ | No features in the test tile. Tsunami zones are evacuation zones, not inundation depths |
| `gw_liquefaction` | Earthquake Liquefaction Potential (GWRC, from GNS 2018) | ◐ (© GWRC, regional CC BY statement) | 2018 basis | ❌ | Regional liquefaction classes. GWRC maps only soils with significant liquefaction potential, so empty means outside those areas, not "no liquefaction" |
| `gw_eq_slope_failure` | Earthquake Slope Failure potential (GWRC, 1995 series) | ◐ (© GWRC) | 1995 basis | ⚠ | Regional susceptibility zones. The layer classes all the land it maps ("1 Low" upwards), so empty means not mapped: about 1,000 parcels, on Kapiti Island and in the eastern hills, some of them steep |

**Tally:** of the 28 rows above (43 source keys), 15 have a licence stated on the dataset (✅) and 13 rely on a portal-wide
statement (◐). None are known to be closed to commercial reuse. Before anything is sold, someone should ask KCDC and GWRC to confirm, in writing, that the
portal-wide statements cover the uncatalogued service layers (the owner makes that contact, not an agent).

## Register: Porirua City

Porirua City (T-24, T-87): the same pipeline with Porirua's own sources, chosen by `COUNCIL=porirua`. District Plan
layers are the Porirua District Plan 2025, operative from 1 November 2025
([council notice](https://poriruacity.govt.nz/your-council/news/public-notices/proposed-district-plan-operative)), from
PCC's ArcGIS Online organisation. Three waters are left out: Wellington Water's licence bars commercial use (D-16). So
are recommended building levels, wind and earthworks zones (PCC publishes none as layers), and ground change (one LiDAR
survey used). Absent columns are left out of Porirua's results, not published empty. Notified Plan Changes 1–6
(published as `*_PDP2025_PC1_6n` layers: flood remapping in the Mana, Pukerua Bay, Aotea/Paremata and Whitby catchments,
and a heritage deletion) are not in force and are not used; on the notified flood maps about 1,000 more parcels would be
in a flood overlay. PCC's draft geohazard layers (landslide and liquefaction, Level A and B) and flood depths are not
used either, nor are the 2025 plan's national grid lines (110/220 kV, crossing about 110 parcels), Ngāti Toa
Rangatira statutory areas, active street frontages and gas transmission stations. `titles` and `nonprimary_parcels` are as
in the register above.

| Key | Dataset (publisher) | Licence | Updated | Fit for parcel use | Notes |
| --- | --- | --- | --- | --- | --- |
| `parcels` | NZ Primary Parcels, layer 50823 (LINZ), by parcel id; city and block membership from PCC's copy (`pcc_parcels`), kept where the parcel's representative point, or at least 1,000 m² of it, lies in the city (`district_outline`) | ✅ LINZ CC BY 4.0 | weekly | ✅ | Whole parcels are published (D-18). Without the LINZ key, PCC's copy is used for every parcel (`geometry_source`) |
| `pcc_parcels` | PCC's public copy of NZ Primary Parcels (Property/Parcel layer 2; 24,128 parcels) | ✅ LINZ CC BY 4.0 | not stated | ✅ | Same fields as LINZ's. Unlike KCDC's copy it includes road (2,137 in the city) and water (19) parcels, which LINZ keeps in layers of their own; they are left out, as in Kāpiti (T-88). A few parcels lie outside the city and are dropped |
| `district_outline` | Three polygons: PCC's city boundary (PropertyAdminExternal layer 4), PCC's two wards (ArcGIS Online `Ward`), and Stats NZ's district polygon (GWRC Region_basemap_P layer 1, © Statistics NZ, CC BY 4.0) | ◐ | not catalogued | — | Land counts where two agree. PCC's boundary and wards are the same 182.5 km² (harbour included), so in practice the outline is PCC's boundary; Stats NZ's is 174.5 km² |
| `zones` | Porirua District Plan 2025 – Zones (`Zone_PDP2025`, field `ZONE`) | ◐ | Oct 2025 | ✅ | |
| `pdp_flood_overland_flow`, `pdp_flood_stream_corridor`, `pdp_flood_inundation` | District Plan 2025 flood hazard overlays (one extent each) | ◐ | Oct 2025 | ⚠ | Modelled extents; no depth or class |
| `pdp_coastal_erosion_current`, `pdp_coastal_erosion_1m_slr`, `pdp_coastal_inundation_current`, `pdp_coastal_inundation_1m_slr` | District Plan 2025 coastal hazard overlays: current erosion and inundation, and with 1 m sea-level rise (the inundation one is the 1-in-100-year storm surge) | ◐ | Oct 2025 | ⚠ | Modelled extents |
| `pdp_tsunami_100yr`, `pdp_tsunami_500yr`, `pdp_tsunami_1000yr` | District Plan 2025 tsunami inundation extents, 1-in-100, 500 and 1,000-year | ◐ | Oct 2025 | ⚠ | Modelled extents |
| `pdp_fault_rupture` | District Plan 2025 fault rupture zones (field `Fault_Name`) | ◐ | Oct 2025 | ✅ | |
| `pdp_heritage_items`, `pdp_heritage_sites` | District Plan 2025 heritage items (points, field `ID`) and historic heritage sites (polygons, field `Name`) | ◐ | Oct 2025 | ✅ | |
| `pdp_notable_trees` | District Plan 2025 notable trees (points, field `Tree_ID`) | ◐ | Oct 2025 | ✅ | |
| `pdp_significant_natural_areas` | District Plan 2025 significant natural areas (field `SiteName`) | ◐ | Oct 2025 | ✅ | |
| `pdp_noise_rail`, `pdp_noise_state_highway` | District Plan 2025 rail noise corridor and state highway noise control boundary | ◐ | Oct 2025 | ✅ | |
| `pdp_coastal_environment` | District Plan 2025 landward extent of the coastal environment | ◐ | Oct 2025 | ✅ | PCC's layer does not reach Mana Island, so empty there is the layer's mapping, not a finding (twelfth review). Nor do the flood and coastal erosion and inundation layers: Mana Island has no such mapping, only tsunami (thirteenth review) |
| `plan_1999_plimmerton_farm` | Porirua City District Plan 1999 – Plimmerton Farm Zone (3.8 km²) | ◐ | 2025 | ✅ | "The Porirua District Plan 2025 does not apply to the area of the Plimmerton Farm Zone." On its 51 parcels `zones` and the `pdp_*` columns are empty or slivers at the zone's edge (a few show 0.0–0.1%): the 1999 plan and Plan Change 18 govern them, and are not compiled |
| `pcc_flood_unmapped` | Flood Hazard – Unmapped Area (PCC Hazards/Flood_Hazards layer 3; 31.5 km², the Horokiri valley) | ◐ | not stated | ✅ | Where PCC has not mapped flood hazard: there an empty `pdp_flood_*` value means not mapped (246 parcels in the 9 Nov 2026 results) |
| `pcc_flood_model_catchments` | Stormwater Model Catchments (PCC Hazards/Flood_Hazards layer 90, fields `Name` and `RepDat`: Wellington Water's stormwater models for Porirua, 2018–2025 reports) | ◐ | 2018–2025 | ⚠ | Which model catchment a parcel lies in, not whether its District Plan flood overlay comes from that model: PCC does not say, the layer has no description, and some overlays likely predate their model (in Whitby the operative plan maps 0.6 ha of inundation in the catchment; notified Plan Changes 1–6 map 37.6 ha). The Horokiri model covers the whole unmapped area. Neighbouring catchments leave small gaps (1.7 km²), so "outside every catchment" is not "never studied" (fourteenth review) |
| `pdp_notable_tree_groups`, `pdp_heritage_settings`, `pdp_heritage_item_extents` | District Plan 2025 notable tree groups (field `ID`), heritage settings and heritage item extents (field `Name`) | ◐ | Oct 2025 | ✅ | |
| `pdp_precincts`, `pdp_height_controls`, `pdp_designations` | District Plan 2025 precincts (`Name`), height controls (`SpecificControl`, `HeightControl` and `HIRB` joined, e.g. "Height Control - Shading C; Height limit - 9m; Standard for the underlying zone") and designations (`Title`, not the requiring authority) | ◐ | Oct 2025 | ✅ | |
| `pdp_special_amenity_landscapes`, `pdp_outstanding_natural_landscapes`, `pdp_coastal_high_natural_character`, `pdp_sites_significance_maori` | District Plan 2025 landscape, natural character and Māori heritage overlays (field `Name`) | ◐ | Oct 2025 | ✅ | |
| `pdp_gas_pipeline_corridor`, `pdp_rail_vibration`, `pdp_radio_height_control`, `pdp_eastern_porirua`, `pdp_northern_growth_area` | District Plan 2025 infrastructure and development-area overlays | ◐ | Oct 2025 | ✅ | |
| `gw_liquefaction` | Earthquake Liquefaction Potential (GWRC, from GNS 2018) | ◐ (© GWRC, regional CC BY statement) | 2018 basis | ❌ | As for Kāpiti: GWRC maps only soils with significant potential, so empty means outside those areas |
| `gw_eq_slope_failure` | Earthquake Slope Failure potential (GWRC, 1995 series) | ◐ (© GWRC) | 1995 basis | ⚠ | Classes all the land it maps, so empty means not mapped |
| `pcc_buildings` | PCC building footprints (PropertyAdminExternal layer 2; 30,409) | ◐ | mostly undated: 29,725 say "Collected from 7.5cm / 10cm GSD Stereo", 684 name photos of 2013 or 2017 (field `SOURCE`) | ⚠ | Their extent matches the city, so coverage is taken as the whole city (`buildings_coverage_pct`). They miss buildings newer than their capture; `unmapped_structure_m2` warns of most of them, and of many trees: in the first district run it was above 0 on 44% of parcels and 50 m² or more on 2,722 (12%) |
| `dem_2023`, `dsm_2023` | Porirua LiDAR 1 m DEM/DSM 2023 (LINZ, nz-elevation `porirua_2023`) | ✅ CC BY 4.0 | 2023 flight | ✅ | 1 m cells. Ground change is not compiled: the earlier survey covering the city (`wellington_2013-2014`) is not used yet |
| `district_flow` | New Zealand LiDAR 1 m DEM, read at 10 m, gaps from the Contour-Interpolated 8 m DEM (LINZ; Geographx for the 8 m) | ✅ CC BY 4.0 | national mosaic | ⚠ | 10 m mosaic over 1740000–1780000 E, 5432000–5468000 N, which takes in the catchments draining into the city |
| `sea_mask` | Sea cells from the `district_flow` grid, as for Kāpiti | ✅ CC BY 4.0 | as `district_flow` | ✅ | |

## Columns: Porirua City

Rows here replace the shared rows below for Porirua; columns not listed have the shared meaning.

| Columns | Kind | Meaning |
| --- | --- | --- |
| `pdp_*` | published | A District Plan 2025 overlay: JSON of its class (or its name, for a layer without classes) → % of parcel area covered; for `pdp_heritage_items` and `pdp_notable_trees`, the points on the parcel. Empty means the parcel is outside it, except where the 2025 plan does not apply (`plan_1999_plimmerton_farm`) and, for the flood overlays, where flooding is not mapped (`pcc_flood_unmapped`). Mana Island has no flood or coastal hazard mapping. PCC does not say which study each flood overlay comes from; in Whitby, Aotea, Mana and Pukerua Bay notified Plan Changes 3–6 (not in force) remap flooding substantially. On parcels the fetch window cuts (`coverage_pct` under 99), overlays cover only the part inside it |
| `building_m2`, `open_ground_m2`, `open_ground_slope_lt5_m2` | derived | Area under PCC's building footprints (mostly undated); the rest of the parcel, outside them; the rest that slopes under 5° (needs LiDAR). 0 m² means no footprint, not no building: check `unmapped_structure_m2`. Empty unless the fetch window covers at least 99% of the parcel; so are the other open-ground and roof columns |
| `buildings_coverage_pct` | derived | Share of the parcel inside the city: PCC's footprints are taken to cover the whole city |
| `pcc_flood_unmapped` | published | JSON of the layer's name → % of parcel area covered: where PCC has not mapped flood hazard (empty: outside that area) |
| `plan_1999_plimmerton_farm` | published | JSON of the layer's name → % of parcel area covered: where the 1999 plan's Plimmerton Farm Zone applies instead of the 2025 plan (empty: outside it) |
| `pcc_flood_model_catchments` | published | JSON of model catchment ("Whitby (model report 2025)") → % of parcel area covered. Not evidence that the parcel's flood overlays come from that model (see the register) |
| `winter_sun_hours_open_mean`, `winter_sun_open_ge3h_pct` | modelled | Hours of direct sun on the ground on 21 June over the clear open ground, from the 2023 DSM (as for Kāpiti otherwise) |
| `wind_obstruction_pct`, `wind_rel_height_m` | derived | Share of the surrounding ±100 m with obstructions over 2.5 m in the 2023 DSM; ground at the parcel relative to the mean ground within ±500 m. Inputs only: no wind class |
| `unit_id`, `appellation`, `parcel_intent`, `survey_area_m2` | published | LINZ parcel id and fields as published. `survey_area_m2` is the whole surveyed parcel's area, repeated on every part of a parcel in several pieces, so don't sum it |
| `unmapped_structure_m2` | modelled | As for Kāpiti, against PCC's footprints and the 2023 LiDAR. They are mostly undated, so more flags here: many are buildings newer than the footprints |
| `geometry_source` | published | `LINZ` (layer 50823) or `PCC mirror` (where LINZ was not fetched or did not return the parcel) |
| `zones`, `zones_total_pct` | derived | `zones`: JSON of District Plan 2025 zone (PCC `ZONE`) → % of parcel area covered; overlapping features of the same zone count once. `zones_total_pct`: their sum |
| `ground_min_m`, `ground_mean_m`, `ground_max_m` | derived | 2023 LiDAR ground height over the parcel, metres NZVD2016 |
| `open_ground_clear_pct` | derived | Share of open ground with nothing standing more than 0.5 m above it in the 2023 DSM (no tree, shrub, hedge, fence, vehicle or building newer than PCC's footprints) |
| `roof_pitch_p50_deg`, `roof_flat_m2`, `roof_north_m2` | derived | From the 2023 DSM inside PCC's footprints: median pitch, area under 5°, area facing north (315°–45°) at 5° or more |
| `upslope_area_max_m2`, `upslope_area_truncated`, `flow_path_m` | modelled | As for Kāpiti, on the 2023 1 m DEM: overland flow within the block's LiDAR window (largest upslope area through the parcel; whether it reaches the window edge or a LiDAR gap; length of flow paths draining at least 2,000 m²). All three empty on parcels under 99% LiDAR coverage |

## Register: national index

The national index (T-100, D-21, D-22; [pilot findings](docs/findings/2026-11-09-national-index-pilot.md)) uses LINZ
data only, read from LINZ's own public ArcGIS services (services.arcgis.com/xdsHIIxuCWByZiCB, no key). Keys match the
tile entries in its `provenance.json`.

| Key | Dataset (owner) | Licence | Updated | Fit for parcel | Notes |
| --- | --- | --- | --- | --- | --- |
| `parcels` | NZ Primary Parcels (LINZ; same as layer 50823) | ✅ LINZ CC BY 4.0 | days behind the Data Service | ✅ | Road parcels, and parcels LINZ itself marks as water or seabed (`Hydro`, `Riverbed`, `Streambed`, common marine and coastal area), are left out of the rows. Every other parcel is a row, whatever its name; how much of it is water is measured (`water_pct`). Some parcels are in the service twice; one is kept (`repeated_records`). The pilot region is its district polygons grown by up to 1 km along the coast, so shore and island parcels are in; a parcel in that margin is left out only if its address, or the nearest address within 1 km, names another district (islands with no address near stay) |
| `roads` | Road parcels from the same layer | ✅ LINZ CC BY 4.0 | as `parcels` | ✅ | For road frontage only |
| `titles` | NZ Property Titles (LINZ; same as layer 50804) | ✅ LINZ CC BY 4.0 | as `parcels` | ✅ | Title number, status and type only; never owners or their number |
| `buildings` | NZ Building Outlines (LINZ; same as layer 101290) | ✅ LINZ CC BY 4.0 | capture dates vary by area (`buildings_captured_to`) | ⚠ | Buildings of 10 m² or more, drawn from aerial photos: they miss buildings newer than the photos, and sheds. In Kāpiti they are 20 m² or more smaller than KCDC's outlines on 22% of parcels: KCDC's are mostly from 2017 photos, drawn wider, and include sheds (sixteenth review) |
| `addresses` | NZ Addresses (LINZ; same as layer 105689) | ✅ LINZ CC BY 4.0 | as `parcels` | ✅ | |
| `lakes`, `rivers`, `land` | NZ Lake Polygons (Topo, 1:50k), NZ River Name Polygons (pilot, a 2018 Topo50 snapshot LINZ does not plan to update) and NZ Coastline polygons (LINZ) | ◐ assumed LINZ CC BY 4.0; to confirm (T-104) | — | ⚠ | For `water_pct` and the map's water. 1:50k: edges can be some metres out |
| `coast` | NZ Coastline - Mean High Water Springs (LINZ) | ◐ assumed LINZ CC BY 4.0; layer number and licence to confirm (T-104) | — | ✅ | Searched to 10 km |
| `elevation` | New Zealand LiDAR 1 m DEM read at 10 m, gaps from the 8 m contour DEM (LINZ; Geographx for the 8 m) | ✅ CC BY 4.0 | national mosaic, surveys 2008–2026 | ⚠ | Per tile plus 5 km, as `district_flow`. 10 m cells smooth small slopes and banks |
| `region` | Stats NZ district polygons, via GWRC (pilot only) | ✅ Stats NZ CC BY 4.0 | — | — | Which parcels are in the pilot region, and the district name |
| `localities` | NZ Suburbs and Localities (LINZ), each naming its district | ◐ assumed LINZ CC BY 4.0; to confirm (T-104) | — | ✅ | The national build's district names where the parcel has no address (T-102); a locality touching several districts names them all, so it decides only where it names one; simplified to 1 m |

The national build (`.github/workflows/national.yml`, T-102) covers the 370 tiles that hold a parcel (`pipeline/nz_tiles.json`),
from the Kermadecs to Campbell Island and the Chathams (92 of them hold only road, water or seabed parcels and give no rows). The elevation sources do not reach the Chathams or the outlying
islands, so their height columns are empty; nor do LINZ's building outlines reach the Chathams.

## Columns: national index

| Columns | Kind | Meaning |
| --- | --- | --- |
| `parcel_id`, `appellation`, `parcel_intent`, `land_district`, `survey_area_m2` | published | LINZ parcel fields as published. Statutory actions are not included: they name who land vests in |
| `area_m2`, `perimeter_m` | derived | From the parcel's shape, m² and m (NZTM2000) |
| `compactness`, `width_m` | derived | 4πA/P² (1 for a circle, about 0.79 for a square, small for a strip); the short side of the smallest rectangle around the parcel |
| `title_count`, `titles_not_found` | published | Titles listed on the parcel; how many were not found current (live or partly cancelled) in the titles layer. Title types are used in the build but never published (D-17, T-106) |
| `rep_x`, `rep_y` | derived | A point inside the parcel (NZTM2000); it decides the parcel's tile |
| `building_count`, `building_m2`, `building_cover_pct`, `largest_building_m2`, `buildings_captured_to` | derived | LINZ outlines: buildings with at least half their area in the parcel; area of outlines inside the parcel and its share of the parcel; the largest counted building; the latest photo date among the outlines touching the parcel. 0 means no outline, not no building |
| `address_count`, `address`, `suburb_locality`, `town_city`, `territorial_authority` | published | Addresses whose point lies in the parcel; the lowest-numbered names it. The district: in the pilot, the region's district polygons, or else the address. In the national build, one name or empty: the parcel's own address; else a LINZ locality that names a single district; where the locality names several (LINZ lists every district a locality touches), the nearest address within 1 km naming one of them; "Area outside Territorial Authority" (offshore islands) only where no address within 1 km says otherwise. Empty where none of these tells (about 0.2% in a test square at Pukekohe) |
| `water_pct` | derived | Share of the parcel's area under water, measured by area: the sea (outside LINZ's Topo50 land outline, fetched at 5 m, so tidal flats count as sea), Topo50 lakes and LINZ's river areas together, each part counted once. All three are 1:50k, so edges can be some metres out, and small shore parcels (a few hundred m²) can be tens of points out. A lake bed held as a parcel (Lake Wairarapa) reads near 100; reclaimed land named as a harbour bed reads near 0. Empty (unknown) where half the parcel or more is sea that no lake or river polygon covers: the outline leaves out many islets and rocks, near the shore and far out (Kapiti Island's reefs, Tarahiki Island, the Snares), and the elevation grid holds a flat sea surface there, so neither can tell a rock from the sea. This also empties true seabed parcels such as marinas; and a rock reaching just inside the outline reads part water (some Kapiti Island reef parts read 29 to 39%). Empty too where the outline has nothing at all (two tiles of reefs east of the Chathams; the Chatham Islands themselves are measured) |
| `road_frontage_via_strip_m` | derived | The part of `road_frontage_m` reached only across a strip under 1 m wide between the lot and the road, often a reserve that bars access: legal frontage may be 0 there |
| `road_frontage_m` | derived | Length of the parcel's boundary within 1 m of a road parcel (LINZ roads often sit 0.2–0.4 m off the lot line), less the short end pieces where a neighbour's side boundary meets it. Across a thin reserve strip between lot and road it still counts, so it can overstate legal frontage there |
| `coast_distance_m`, `coast_over_10km` | derived | Distance to the mean high water springs line; empty and `coast_over_10km` true when more than 10 km |
| `ground_mean_m`, `ground_min_m`, `ground_max_m` | derived | Ground height over the parcel's 10 m cells, metres NZVD2016 |
| `slope_mean_deg`, `slope_max_deg`, `flat_pct`, `steep_pct`, `low_lying_pct` | derived | Slope of the 10 m ground: mean, maximum, share under 5°, share over 15°; share of cells under 5 m above sea level. At 10 m, slope reads about 2° gentler than on the 1 m ground (up to 5°), so small sloping sections can read flat; the parcel report has 1 m slope |
| `lidar_pct` | derived | Share of the parcel's cells from LiDAR rather than the 8 m contour DEM |
| `ground_cells`, `ground_cells_pct`, `elevation_from` | derived | 10 m cells used, and the share of the parcel's own cell centres that have ground (under 100 where some have no ground data). For a parcel of 10 ha or more with over a tenth of its area outside the elevation read for its tile (the tile plus 5 km), it is the share of the whole parcel, so a national park's heights are seen to describe only part of it. A parcel too small to hold a cell centre is read at its point (`elevation_from` `point`: only mean height and slope) |
| `upslope_area_max_m2`, `upslope_truncated` | modelled | Largest area draining through the parcel on the 10 m ground (D8 flow); true where that catchment may reach past the tile plus 5 km |
| `geometry_wkb` | derived | The parcel's shape simplified to 0.5 m, for maps |

## Parcel report (national)

The parcel report (T-101, `pipeline/parcel_report.py`) compiles the shared columns below for one parcel with the national
settings (`pipeline/councils/national.py`). Its sources: `linz_parcels_service`, `titles` and `linz_buildings` from
LINZ's public ArcGIS services as in "Register: national index" (or the LINZ Data Service with the key, which adds
`nonprimary_parcels`); `dem_national` and `dsm_national`, the New Zealand LiDAR 1 m DEM and DSM mosaics (LINZ,
CC BY 4.0, surveys 2008–2026; the report names each survey under the parcel, with its dates, producer and licensor);
and `district_flow` over 8 km around the parcel. Differences from the shared meanings: `building_m2` is the area under
LINZ's national building outlines; `easements_n` and `land_covenants_n` are empty without the key; council columns
(zones, overlays, flood, three waters) and ground change are not compiled.

## Compiled columns (per parcel, table `units`)

> **Second review (T-46 to T-51, 7 Nov 2026).** The problems it found are fixed and the district was rebuilt on
> 7 Nov 2026 (run 42358053821, commit `4b64604`). One small fix waits for the next rebuild: 3 coastal parcels' lowest
> ground still reads the flat sea value (−0.56 m). See [the second review](docs/findings/2026-11-07-second-review.md).

**sha256 in provenance:** the hash of the data as the pipeline stored it after download (re-serialised GeoJSON, or the LiDAR array), which identifies what each block was compiled from; it cannot be reproduced from the server's response bytes.

**Overlay class fields** (detail for the overlay rows below): JSON of class name → % of parcel area covered. Overlapping features of the same class count once; overlaps under 0.5 m² are ignored. Class field: `zones` the operative District Plan zone (`ePlan_Zone`; `zones_total_pct` is the sum, above 100 where KCDC stacks zones of different types on a parcel; the layer's `PDP_ZONE` holds older names for some features); `ovl_flood_hazard` and `flood_*` the flood class (`ZONE`); `tsunami_zones` the evacuation zone; `ovl_fault_avoidance` fault name and certainty; `ovl_noise_corridor` the boundary id (one large corridor has no name or id in the source and reads "Noise Corridor (no name in source)"); `gw_liquefaction` and `gw_eq_slope_failure` their class. Empty means the parcel is outside every feature of the layer: for a hazard extent (flood, tsunami, fault, coastal) that is outside the mapped hazard, within the area the council modelled; for a layer that classes all land (`zones`, `gw_eq_slope_failure`) it means not mapped. KCDC's flood layers and recommended building levels cover only its flood models (roughly 1763700–1786100 E, 5458400–5489600 N, and not Kapiti Island); outside them an empty flood column means not modelled. Layers without a class field (`ovl_coastal_env`, `wind_*`, `earthworks`) give the overlay's name. Before T-40 (6 Nov 2026) shares were summed across overlapping features and could exceed 100%.

**Kind:** **published** = a value as the source publishes it · **derived** = calculated exactly from published data
(an overlap, a distance, a statistic of LiDAR cells) · **modelled** = an estimate from a model with stated simplifications.

| Columns | Kind | Meaning |
| --- | --- | --- |
| `unit_id`, `appellation`, `parcel_intent`, `survey_area_m2` | published | LINZ parcel id and fields as published. `survey_area_m2` is the area of the whole surveyed parcel, which LINZ repeats on every part of a parcel in several pieces (Kapiti Island's 17.6 km² is on each of its 36 parts), so don't sum it |
| `titles` | published | LINZ title references on the parcel, as published. Not served in public mode by the query service, because each is a key to owner records (D-15) |
| `unit_source` | derived | What a unit is: `parcels` (a primary parcel); building outlines only in a run without parcels |
| `district_share_pct` | derived | Share of the parcel's area inside `district_outline`; under 100 for parcels crossing the district boundary (down to 0.1% for large parcels with 1,000 m² inside). On those parcels, values cover different extents: council layers cover what the council maps (zoning often covers the whole parcel, other layers stop at the boundary); terrain and building columns cover the part inside the block's fetch window (`coverage_pct`); the district catchment covers the parcel's cells on the 10 m mosaic |
| `geometry_source` | published | `LINZ` (layer 50823) or `KCDC mirror` (where LINZ was not fetched or did not return the parcel) |
| `rep_x`, `rep_y`, `bbox_xmin`, `bbox_ymin`, `bbox_xmax`, `bbox_ymax` | derived | A point inside the parcel and the parcel's bounding box, NZTM2000 metres, for area queries |
| `block_id` | derived | The block the parcel was compiled in: `xmin_ymin_size` (NZTM2000, metres) |
| `area_m2`, `coverage_pct` | derived | Polygon area (the whole parcel, inside the district or not); share of it inside the block's fetch window, which reaches at most 1 km beyond the block. Terrain and building columns cover only that share; council overlays cover the council features touching the parcel, which may reach beyond the window. Queries use parcels at 99% or more |
| `lidar_cells`, `lidar_coverage_pct` | derived | 1 m LiDAR cells with ground values on the parcel, and their share of the parcel's cells, scaled by the share of the parcel inside the LiDAR window (sea cells count as covered on a parcel that has land LiDAR; at least 0.1 when the parcel has any cells); 0 means outside the LiDAR surveys and terrain columns are empty. Below 100%, terrain values describe only the covered part; the terrain-based queries need at least 99% |
| `title_types`, `title_count` | published | Distinct LINZ title types on the parcel (for example Freehold, Cross lease) and number of title references. Public mode serves the count only (D-15, D-17) |
| `easements_n`, `land_covenants_n` | derived | LINZ easement and covenant parcels overlapping it by more than 1 m². 0 means none surveyed as a parcel, not none at all: an easement registered without a survey parcel is not counted |
| `zones`, `zones_total_pct` | derived | `zones`: JSON of operative District Plan zone (KCDC `ePlan_Zone`) → % of parcel area covered; overlapping features of the same zone count once. `zones_total_pct`: the sum, above 100 where KCDC stacks zones of different types on the parcel |
| `ovl_*`, `flood_*` (polygon layers), `wind_*`, `tsunami_zones`, `earthworks`, `gw_*` | derived | JSON of class name → % of parcel area covered, using the layer's own class field (or the overlay's name where it has none). Overlapping features of the same class count once; overlaps under 0.5 m² are ignored |
| `ovl_heritage_places`, `ovl_notable_trees` | derived | JSON list of the heritage or tree points inside or on the parcel boundary: KCDC id and significance text (empty significance as null). Before T-44 (7 Nov 2026), points within 1 m, without ids |
| `ground_min_m`, `ground_mean_m`, `ground_max_m` | derived | 2024–25 LiDAR ground height over the parcel, metres NZVD2016 |
| `slope_p50_deg`, `slope_p90_deg` | derived | Median and 90th-percentile ground slope over the parcel's 1 m cells |
| `building_2021_m2`, `open_ground_m2`, `open_ground_slope_lt5_m2` | derived | Area under KCDC's 2021 building outlines; the rest of the parcel, outside those outlines (present without LiDAR); the rest that slopes under 5° (needs LiDAR). All within the fetch window, counting 1 m cells. KCDC's outlines miss some houses and everything built since 2021, so 0 m² means no outline, not no building: check `unmapped_structure_m2` (D-19). Empty, not 0, unless the outlines cover at least 99% of the parcel (`buildings_coverage_pct`) and the fetch window covers at least 99% (`coverage_pct`); so are the other columns measured on open ground or roofs (T-73, T-76). The horizon, sky-view and wind columns stay: their viewpoint must also be clear of anything standing in the 2024–25 DSM |
| `unmapped_structure_m2` | modelled | A warning: the largest building-like structure on the parcel that no 2021 outline covers, from the 2024–25 LiDAR. That is 2.5–15 m above the ground, on a surface that is locally a plane (pitched roofs pass), at least 3 m wide and more than 2 m from any outline. From 40 m², a building may stand here that KCDC's outlines lack (D-19, T-81). Tested by hiding the 3,552 outlines of 60 m² or more in a 2.5 km tile: it found 90% (94–98% of roofs under 26°, 43% of roofs over 30°, 63% of buildings of 60–80 m²); of buildings of 40–60 m² (sleep-outs, small units) it found only about 22% (eleventh review). Many flags are trees: 163 of that tile's 2,557 parcels are flagged, mostly by round tree crowns. 0 means nothing found, not certainly no building. Empty where the LiDAR covers under 99% of the parcel. The building columns are not changed by it |
| `buildings_coverage_pct` | derived | Share of the parcel where the 2021 building outlines were captured (`buildings_capture_area`, within the district). Before T-76 (8 Nov 2026) the layer's bounding box was used, which took in 586 parcels without outlines |
| `canopy_gt3m_open_pct` | derived | Share of open ground where the surface is more than 3 m above ground (trees or structures) |
| `open_ground_clear_pct` | derived | Share of open ground with nothing standing more than 0.5 m above it in the 2024–25 DSM (no tree, shrub, hedge, fence, vehicle or building newer than the 2021 outlines) |
| `dz_2021_2025_mean_m`, `dz_2021_2025_absmax_m` | derived | Ground change 2021 → 2024–25, mean and largest single cell; not offset-corrected: subtract `lidar_epoch_offset_block_m` |
| `dz_2021_2025_clear_pct`, `dz_2021_2025_clear_mean_m` | derived | The share of the parcel's LiDAR cells that are clear ground in 2025 (DSM within 0.5 m of the DEM), and the mean ground change on those cells only (at least 50 cells; not offset-corrected). Comparing it with `dz_2021_2025_mean_m` separates change on open ground from change under vegetation. In the T-29 photo check, a clear-ground rule kept 10 of 13 real changes and dropped 4 of 8 vegetation hits and both artefacts |
| `lidar_epoch_offset_block_m` | derived | The block's LiDAR epoch offset: median 2024–25 minus 2021 ground on flat (slope under 2°), clear ground (DSM within 0.5 m of the DEM, which excludes roofs and trees), from at least 1,000 cells; LiDAR only since T-54 (before, the 2021 building outlines were also excluded); district blocks range from about +0.03 to +0.11 m |
| `ww_mh_dist_m`, `ww_mh_tied_ids` | derived | Nearest in-use council wastewater manhole (node type WWMH) that has an invert, within 150 m: distance, id, invert (NZVD2016). Where several are equally near (within 5 cm, for example two inside the parcel), the deepest invert is reported and all their ids are listed in `ww_mh_tied_ids`. Before T-44 any wastewater node with an invert counted, including cleaning eyes and valves |
| `ww_mh_id`, `ww_mh_invert_nzvd2016` | published | The id and invert level of that manhole, as KCDC publishes them |
| `ww_head_ground_min_minus_invert_m` | derived | Parcel's lowest ground minus that invert: a rough fall available for gravity drainage, before pipe cover and grade |
| `ww_pipe_dist_m`, `ww_pipe_tied_ids` | derived | Nearest in-use council wastewater pipe within 150 m (where several tie within 5 cm, the worst condition grade, all ids listed in `ww_pipe_tied_ids`): distance (derived), id, material code, diameter, install year, condition grade (1 very good to 5 very poor; 0 treated as not graded). Install year: KCDC records about 1,350 pipes as 1979 and 1,930 as 1980, against at most about 220 in any other year except 2023, so many of those dates may be placeholders |
| `ww_pipe_id`, `ww_pipe_material`, `ww_pipe_dia_mm`, `ww_pipe_year`, `ww_pipe_condition_grade` | published | That pipe's id, material code, diameter (mm), install year and condition grade, as KCDC publishes them (see `ww_pipe_dist_m` for caveats), except that KCDC's condition grade 0 ("not graded") is published empty (T-79) |
| `sw_mh_dist_m` | derived | Distance to the nearest in-use council stormwater manhole (node type SWMH) with an invert, within 150 m; not culvert ends, sumps or soakage |
| `sw_mh_invert_nzvd2016` | published | That manhole's invert level (NZVD2016), as KCDC publishes it |
| `ws_pipe_dist_m`, `ws_pipe_tied_ids` | derived | Distance to the nearest in-use council water main within 150 m: reticulation, rider or trunk main carrying treated water, chosen by KCDC pipe type (service connections, scour and plant pipework, and raw-water pipes are left out; a few reticulation mains are themselves as small as 20 mm). Where several tie within 5 cm, the largest is reported and all ids are listed in `ws_pipe_tied_ids`. Before T-54 (8 Nov 2026) the nearest pipe was usually a service connection |
| `ws_pipe_dia_mm`, `ws_pipe_type` | published | That main's nominal diameter (mm) and KCDC pipe type (`RETI` reticulation, `RIDE` rider, `TRNK` trunk), as KCDC publishes them |
| `rbl_in_parcel_n`, `rbl_in_parcel_max_nzvd2016`, `rbl_in_parcel_max_minus_ground_mean_m` | derived | Recommended building level points inside the parcel (empty, not 0, where there are none: KCDC issues them only inside its flood models, so none does not mean no flood risk); highest; how far it sits above mean ground (a floor-height requirement) |
| `rbl_max_nzvd2016`, `ground_min_minus_rbl_m` | derived | Highest recommended building level within 10 m, and lowest ground minus it. Picks up upslope values; don't read it as flood depth |
| `winter_sun_hours_open_mean`, `winter_sun_open_ge3h_pct` | modelled | Hours of direct sun on the ground on 21 June (hourly samples, NZST) over the clear open ground (`open_ground_clear_pct`): the mean, and the share getting 3 hours or more. Ground under trees is not counted; empty if no open ground is clear. Before T-43 (7 Nov 2026) this measured sun on the surface, which on wooded ground is the canopy. Shadows from buildings, trees and terrain within 300 m in the 2024–25 DSM; farther ranges are not counted |
| `roof_pitch_p50_deg`, `roof_flat_m2`, `roof_north_m2` | derived | From the 2024–25 DSM inside 2021 building outlines: median pitch, area under 5°, area facing north (315°–45°) at 5° or more |
| `roof_solar_rel_pct` | modelled | Clear-sky direct sun on the roof surface (shaded as above) over three representative days (21 June, 20 March, 21 December), as % of an unshaded horizontal surface at the same place. No cloud or diffuse light; compare roofs with each other, not with kWh figures |
| `upslope_area_max_m2`, `upslope_area_truncated`, `flow_path_m` | modelled | All three empty on parcels under 99% LiDAR coverage (T-81). Overland flow on the 2024–25 1 m DEM (D8; depressions and flats drained by priority-flood, `flow.py`) within the block's LiDAR window: largest upslope area draining through the parcel; whether that upslope area reaches the window edge or a LiDAR gap over land, so may be larger (true for river corridors: use `catchment_area_max_m2`); and length in metres of flow paths across the parcel draining at least 2,000 m². Ignores stormwater pipes, culverts and bridges, so urban flows are overstated |
| `catchment_area_max_m2`, `catchment_truncated` | modelled | Largest upslope area draining through the parcel on the 10 m district mosaic (`district_flow`), from 10 m cells whose centre is in the parcel (or the cell holding it, for a parcel under about 100 m²), so whole river catchments are counted; and whether that upslope area reaches the mosaic edge (a parcel reaching beyond the mosaic counts only its cells on it). The mosaic treats as sea the cells with no value in the 8 m contour DEM and no higher than 0.5 m, because the 1 m DEM stores the sea as a flat surface near −0.6 m; streams drain into it. Before T-47 (7 Nov 2026), coastal streams were routed through that flattened sea, and any 10 m cell touching a parcel counted. Checked: Waikanae 148 km² and Ōtaki 374 km² near their mouths |
| `level_open_cut_m3`, `level_open_fill_m3` | derived | Cut and fill to bring all open ground to its median level |
| `platform_15m_earthworks_min_m3` | modelled | Smallest earthworks for a 15 m × 15 m level platform lying wholly on the parcel's open ground, estimated from the spread of ground levels; empty where no such square fits |
| `wind_obstruction_pct`, `wind_rel_height_m` | derived | Share of the surrounding ±100 m (square) with obstructions over 2.5 m in the DSM; ground at the parcel (1 m DEM) relative to the mean ground within ±500 m on the 10 m district mosaic, with the sea (masked as above) at 0 m. Inputs to wind exposure, not an exposure rating: a modelled exposure class built from these two disagreed with KCDC's wind zones (T-37) and is withheld |
| `horizon_mean_deg`, `horizon_north_deg`, `sky_view_pct` | derived | From the most open spot on the section at 1.6 m eye height (the clear open-ground cell farthest from buildings, trees and the boundary; empty if no open ground is clear): mean horizon angle in 16 directions, the highest towards north (N, NNE, NNW), and sky view (100 = open sky) |
