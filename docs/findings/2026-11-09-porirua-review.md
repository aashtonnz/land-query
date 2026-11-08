# Twelfth fresh-eyes review: Porirua (T-89, 9 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `ae37a23..1d01a44` (T-86 to T-88: per-council settings and
Porirua) and the first Porirua results (run 42499625052 at `b06e418`). It was told that road and water parcels had
already been found and left out in code.

- **Spot checks.** 14 parcels end to end against PCC's live layers and LiDAR: coast, harbour, hills, the fault, the
  city's edges and Mana Island.
- **Membership.** City membership recomputed from scratch.
- **Kāpiti.** A Kāpiti tile compiled before and after the generalisation, and compared.
- **Tests.** 25 mutants of the per-council code.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | The District Plan 2025 does not apply in the 1999 plan's Plimmerton Farm Zone (PCC's own layer says so), yet its 50 parcels were published with empty zones and `pdp_*` columns, which read as "outside". | Confirmed, serious | T-90 |
| 2 | PCC has not mapped flood hazard in the Horokiri valley (its "Flood Hazard – Unmapped Area", 31.5 km²): 208 parcels there read empty flood columns. | Confirmed, serious | T-90 |
| 3 | Porirua's `about` was Kāpiti's text: attribution to KCDC, Kāpiti's forest section and railway note, KCDC's flood models. | Confirmed, serious | T-90 |
| 4 | Notable tree groups, heritage settings and heritage item extents were not fetched, so `[]` read as "none" on 17 + 8 parcels that have them. | Confirmed, serious | T-90 |
| 5 | PCC's coastal environment layer does not reach Mana Island. | Suspected, serious | T-90 (disclosed) |
| 6 | Notified Plan Changes 1–6 (flood remapping, a heritage deletion) are not in force, are not used, and were not disclosed. | Confirmed, minor | T-90 (disclosed) |
| 7 | District Plan 2025 layers that matter for land decisions were not fetched: precincts, height controls, designations, landscapes, coastal natural character, sites of significance to Māori, the gas pipeline, rail vibration, radio height control, development areas. PCC's draft geohazard layers and flood depths were not used. | Confirmed, minor | T-90 (fetched; drafts disclosed) |
| 8 | The footprints' dates in `SOURCES.md` were unsupported (29,725 of 30,409 are undated); "one survey only" was false (2013–14 LiDAR covers the city). | Confirmed, minor | T-90 |
| 9 | `unmapped_structure_m2` flags far more than `SOURCES.md` implied (above 0 on 44%, 50 m² or more on 12%). | Confirmed, minor | T-90 |
| 10 | The service named the mirror as a source only for "KCDC mirror". | Confirmed, minor | T-90 |
| 11 | The service accepted another council's results. | Confirmed, minor | T-90 |
| 12 | Shared column meanings still carried Kāpiti text for Porirua (winter sun, wind, survey area); Porirua's QA height checks have no matching fields (n = 0). | Confirmed, minor | T-90 in part (QA open) |
| 13 | The outline is in effect PCC's boundary (its boundary and wards differ by 1.2 ha). | Confirmed, minor | Already stated in `SOURCES.md` |
| 14 | The READMEs, `fetch_results.py` and `server.py` did not mention `COUNCIL` or `porirua-results`. | Confirmed, minor | T-90 |
| 15 | 14 of 25 mutants survived. | Confirmed, minor | T-90 |

Checked and correct:
- All 19 polygon layers matched PCC's live layers exactly on 14 parcels, and ground levels matched the LiDAR.
- Every layer is the 2025 plan version, with the right class fields.
- Membership is exact: 0 wrongly in, 0 wrongly out, no parcel in both councils.
- Kāpiti is unchanged.
- The road fix works.
- Public mode leaks nothing about people.

## Not checked

- **Blocked by the proxy:** PCC's ArcGIS Online licence wording.
- **Open questions:** whether the plan puts Mana Island in the coastal environment; the footprints' capture dates.
- **Needs the LINZ key:** LINZ geometry.
- **Not run:** `finish.py` for Porirua.

## T-90: fixes (9 Nov 2026)

- **Where the plan applies** (1, 2, 5, 6).
  - New Porirua columns `plan_1999_plimmerton_farm` (the 1999 plan's zone, where the 2025 plan does not apply) and
    `pcc_flood_unmapped` (where PCC has not mapped flood hazard).
  - P1 now excludes parcels in the unmapped area.
  - `SOURCES.md` and `about` say what an empty value means there, that the coastal environment layer misses Mana
    Island, and that Plan Changes 1–6 and the draft geohazard layers are not used.
- **More layers** (4, 7). 15 more District Plan 2025 layers: notable tree groups, heritage settings and item extents,
  precincts, height controls, designations, four landscape and cultural overlays, five infrastructure and
  development-area overlays. P3 includes the tree groups and heritage settings and extents.
  - A 2 km Plimmerton tile compiles with 93 columns. 15 parcels are marked Plimmerton Farm, 14 of them with empty zones.
    Height controls are on 113 parcels and precincts on 15.
- **Per-council text** (3, 12, 14). Each council's settings carry its own `about` text. Porirua column rows cover
  winter sun, wind and survey area. The server, `fetch_results.py` and the README name the council.
- **Service** (10, 11). The mirror source uses the council's own copy; another council's results are refused.
- **Wording** (8, 9). The footprints are described as mostly undated, the 2013–14 survey is named as not yet used, and
  the warning's district rate is given.
- **Tests** (15).
  - Rules moved into tested functions: the outline from polygons, roads and water left out, the council's columns, the
    renamed building column, building coverage, the queries (now in `inverse_queries_defs.py`).
  - Of 11 mutants of the kind that survived, all 11 are caught.
  - Both councils pass all 23 service tests.
  - The Kāpiti tile still compiles identically, and Kāpiti's queries are unchanged.
- **Still open:** Porirua's QA height checks (no matching fields in PCC's layers), and ground change from the 2013–14
  survey.

## T-90: republished (9 Nov 2026)

- **Run.** Run 42506899575 compiled all 17 blocks at `357b58d` and published to `porirua-results`. No source failed,
  and the service checks passed before publishing.
- **Checked on the published results:**
  - 21,954 parcels with no road or water parcels. 6 lack LINZ geometry (was 2,162); 10 LINZ parcels are not in PCC's
    copy.
  - 93 columns. `plan_1999_plimmerton_farm` is on 51 parcels, 46 of them with no zone (the 2025 plan does not apply).
    `pcc_flood_unmapped` is on 246.
  - The new layers carry values: height controls on 2,059 parcels, precincts 5,685, designations 1,267, notable tree
    groups 18, heritage settings 43.
  - P1 304 (was 587, now without roads and the unmapped flood area), P2 402, P3 1,803. The flow model against PCC's
    flood overlays has a lift of 1.87.

A thirteenth fresh-eyes review follows, under fresh-eyes review 1.1.

# Thirteenth fresh-eyes review (T-91, 9 Nov 2026)

A new reviewer reviewed `1d01a44..357b58d` (T-90) and the republished Porirua results (run 42506899575).

- **Whole city.** It recomputed all 36 polygon layers for all 21,954 parcels from PCC's and GWRC's live layers. Apart
  from 4 slivers and two parcels the fetch window cuts, all match. LiDAR values match exactly on 13 of 14 parcels.
- **Kāpiti.** Kāpiti's service output is byte-identical before and after T-90.
- **Tests.** It ran 22 mutants.

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | Mana Island has no flood or coastal erosion and inundation mapping at all, yet its empty values read as "outside the hazard". | Suspected, serious | T-92 (disclosed) |
| 2 | 48.9 km² of the city (about 300 parcels more than half, including about 115 Medium Density or Mixed Use) lies outside every stormwater model the flood overlays come from, and outside the unmapped area: an empty flood value there may mean never studied. | Suspected, serious | T-92 |
| 3 | P2's top row was Lot 200 DP 600849, almost all in the Plimmerton Farm Zone, through a 56.5 m² sliver; 54 of its 402 rows had under 1% coverage. | Confirmed, serious | T-92 |
| 4 | Not every Plimmerton Farm parcel has empty plan columns (edge slivers); the `pdp_*` row said empty always means outside. | Confirmed, minor | T-92 |
| 5 | P1's question and the `building_m2` row still dated the footprints to 2013–17. | Confirmed, minor | T-92 |
| 6 | Height controls dropped the height limit: only `SpecificControl` was used. | Confirmed, minor | T-92 |
| 7 | National grid lines, Ngāti Toa statutory areas, active street frontages and gas stations were neither fetched nor disclosed. | Confirmed, minor | T-92 (disclosed) |
| 8 | `pcc_flood_unmapped` is understated on two large parcels the fetch window cuts. | Confirmed, minor | T-92 (disclosed for all overlays) |
| 9 | Counts in `SOURCES.md` had drifted (50, 210). | Confirmed, minor | T-92 |
| 10 | 16 of 22 mutants survived; refusing another council's results had no test. | Confirmed, minor | T-92 |
| 11 | Heritage and Māori-site names (such as "House at 4 Kenepuru Drive" and urupā names) are served in internal mode. They are plan items about land, withheld publicly with all PCC columns. | Note | None |

## T-92: fixes (9 Nov 2026)

- **Flood and coastal coverage** (1, 2, 8).
  - A new Porirua column, `pcc_flood_model_catchments` (PCC's Stormwater Model Catchments, by model name), shows
    which flood model a parcel lies in. An empty value means outside every model, where an empty flood value may mean
    never studied. It is pending until the next Porirua rebuild.
  - `SOURCES.md` and `about` disclose Mana Island's lack of flood and coastal mapping, and that overlays cover only
    the part of a parcel inside its fetch window.
- **P2** (3). Rows need at least 1% of the parcel in a sea-level-rise overlay, and none in the Plimmerton Farm Zone.
- **Wording** (4, 5, 7, 9). The `pdp_*` row names its exceptions; the footprints are "mostly undated"; the layers not
  used are listed; the counts are 51 and 246.
- **Height controls** (6). Labelled with all three fields joined, for example "Height Control - Shading C; Height
  limit - 9m; 3m x 45°".
- **Tests** (10).
  - New tests cover Porirua's layers, URLs, class labels and query filters, the service's refusal of another
    council's results, and the council text in `server.py` and `fetch_results.py`.
  - Of 12 mutants of the surviving kind, 11 are caught. The twelfth (Porirua's own sources for
    `buildings_coverage_pct` removed) is equivalent: the mapped Kāpiti rule gives the same sources.

## T-92: rebuilt (9 Nov 2026)

- **Run.** Run 42512213482 compiled all 17 blocks at `daf1c0c` and published. No source failed, and the service checks
  (including the schema check with the new column) passed before publishing.
- **Checked on the published results:**
  - 21,954 parcels, 94 columns.
  - `pcc_flood_model_catchments` is on 21,791 parcels. 163 lie wholly outside every model and outside the unmapped
    area; partial overlaps show their share.
  - Height controls carry their limits ("Height Control - Shading C; Height limit - 9m; ...").
  - P2 has 348 rows (was 402), none in the Plimmerton Farm Zone. P1 304, P3 1,803.

A fourteenth fresh-eyes review follows.

# Fourteenth fresh-eyes review (T-93, 9 Nov 2026)

A new reviewer reviewed `357b58d..daf1c0c` (T-92) and took a fresh look at the whole Porirua product. Its method
caught what earlier reviews had missed. It compared each layer's area, as the pipeline reads it, with PCC's own
`Shape__Area`, and rebuilt shapes from ArcGIS's own rings. Earlier reviews had read PCC's layers the same way as the
pipeline.

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | Overlays were inflated where PCC's shapes are invalid. The compiler repaired them with `buffer(0)`, which fills the holes of some multi-ring polygons: the gas pipeline corridor read as 7.05 km² (true 0.667), overland flow 1.04 (0.86), inundation 7.67 (6.97), tsunami +9–11 ha each. 206 parcels were wrongly in the gas corridor, 115 in overland flow and 67 in inundation. | Confirmed, serious | T-94 |
| 2 | `pcc_flood_model_catchments` read as "this land was modelled", but PCC does not say which model each operative flood overlay comes from. The Horokiri model covers the whole unmapped area, and in Whitby the operative plan maps 0.6 ha of inundation where the notified Plan Changes map 37.6 ha. | Confirmed, serious | T-94 |
| 3 | The catchments leave small gaps (1.7 km²), so "outside every model" is not "never studied"; 19 of the 163 parcels outside have flood overlays. | Confirmed, minor | T-94 |
| 4 | Text left stale after the rebuild ("after the next rebuild", "about 300", "since 2017", a height-control example not in PCC's data). | Confirmed, minor | T-94 |
| 5 | One column row described three columns. | Confirmed, minor | T-94 |
| 6 | P2's thresholds were mismatched: 1% to qualify, but any sliver of a current extent or the Plimmerton Farm Zone excluded; 4 rows had under 5 m² of footprint. | Confirmed, minor | T-94 |
| 7 | 12 of 14 T-92 mutants survived: the tests looked for text in the SQL, not what it selects. | Confirmed, minor | T-94 |
| 8 | Porirua's QA summary uses Kāpiti's names (n = 0), and the measure check's parcel universe is unexplained. | Confirmed, minor | Open |

Checked and correct:
- 19 parcels end to end in places earlier reviews had not covered: areas, layers (apart from finding 1) and LiDAR
  match.
- Height labels are PCC's three fields.
- P1–P3 reproduce.
- Kāpiti is unchanged by T-92.
- Public mode leaks nothing about people.

## T-94: fixes (9 Nov 2026)

- **Shape repair** (1).
  - Invalid source shapes are repaired with `make_valid`, keeping polygon parts (`overlays.repaired`). That gives
    exactly PCC's `Shape__Area` for the gas corridor, overland flow, inundation and tsunami.
  - Kāpiti's invalid shapes come out the same area either way. Checked on all of its layers: no difference.
    Kāpiti's test tile still compiles identically, so Kāpiti needs no rebuild.
  - A test reproduces the gas corridor's shape: one ring round the outside and back round the inside.
- **Flood model catchments** (2, 3).
  - Labelled with the model's report year ("Whitby (model report 2025)").
  - Described as which model catchment a parcel lies in, not evidence that its flood overlay comes from that model.
    The register gives the Whitby and Horokiri examples and the gaps.
  - `about` now says PCC does not say which study each flood overlay comes from.
- **P2** (6). Rows need 1% in a sea-level-rise overlay, under 1% in the current extents and the Plimmerton Farm Zone,
  and at least 10 m² of footprint.
- **Wording** (4, 5). Stale text fixed; one row per column.
- **Tests** (7). P1–P3 now run on a small table of made-up parcels, one for each condition, so a test checks what the
  SQL selects. All 9 mutants of this round are caught, including putting `buffer(0)` back.

## T-94: rebuilt (9 Nov 2026)

- **Run.** Run 42517549416 compiled all 17 blocks at `11dfb3d` and published. No source failed; the service checks
  passed.
- **The counts fell by exactly what the review predicted:**
  - gas pipeline corridor 385 → 179 parcels (206 fewer);
  - overland flow 1,257 → 1,142 (115);
  - inundation 5,432 → 5,365 (67);
  - tsunami 1-in-1,000-year 928 → 927;
  - designations 1,267 → 1,086 (the gas network designation was inflated too).
- **Spot checks.** Lot 3 DP 337497 is no longer in the corridor. Catchment labels carry their report years.
- **Queries.** P1 310, P2 385, P3 1,803; the flow check's lift is 1.91.

A fifteenth fresh-eyes review follows.
