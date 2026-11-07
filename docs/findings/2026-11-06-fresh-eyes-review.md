# Fresh-eyes review of the pipeline and district results (6 Nov 2026)

T-39. A separate reviewer started from the repository alone (`pipeline/`, both workflows, `SOURCES.md`, D-12 and the
`kapiti-results` branch from run 42179435755, 27,614 parcels × 77 columns), not from earlier summaries. The main
counts below were re-run before this note was written. Fixes are tracked as T-40 to T-45 on the board. Each comes with a
check in `pipeline/test_review.py` or a SQL count that fails on the current code.

## What could not be checked

Comparing parcel values with the raw KCDC, GWRC and LINZ layers was blocked: the reviewer's session cannot reach
`maps.kapiticoast.govt.nz`, `mapping.gw.govt.nz`, `services2.arcgis.com` or GitHub artifact storage, and LINZ needs the
repository key. The LiDAR checks read the LINZ elevation bucket directly. The raw-source sample check moves to T-45, to
run through GitHub Actions, which can reach those hosts.

## Findings, most serious first

| # | Problem | Extent | Task |
| --- | --- | --- | --- |
| 1 | Zone and overlay shares are summed across overlapping features (`compile_tile.py`, label loop), so a parcel can be 200% one zone. Labels mix the proposed-plan field `PDP_ZONE` with the legacy `ZONE` field, and Q1 knows only the new names. | 1,719 parcels have a single class above 100%; 7,599 carry only legacy labels; Q1 would gain 121 parcels if it read them. Example: Lot 14 DP 43617, `High Density Residential Zone` 200%. | T-40 |
| 2 | Query provenance has `sha256: null` and `fetched: null` for every source. `inverse_queries.py` reads fields that `merge_blocks.py` doesn't write, most fetchers never record a fetch time, and feature counts are summed over overlapping windows (titles: 42,982). | All 3,428 query rows. | T-41 |
| 3 | Overland flow (`upslope_area_max_m2`, `flow_path_m`) stops at the block's fetch window and at the LiDAR edge. | District maximum is 6.33 km² against a Waikanae catchment of about 140 km²; river-corridor parcels are wrong by orders of magnitude. `flow_path_m` counts cells, so diagonal steps are short by up to 41%. | T-42 |
| 4 | "Winter sun on open ground" tests the DSM surface, which is the tree canopy on wooded ground; the outlook viewpoint can sit under trees. | Parcels with ≥80% canopy average 3.9 h of winter sun but 5.7% sky view; 41 parcels have ≥90% canopy and ≥90% sunlit open ground. | T-43 |
| 5 | `wind_rel_height_m` fills sea cells with the window's mean height, and its 500 m smoothing runs past windows that extend only about 235 m. | 366 coastal parcels read below −5 m, so beachfront looks sheltered (likely part of why the wind class failed in T-37); up to 4 m error near block edges. | T-42 |
| 6 | The "inland Waikanae" manhole anomaly is in Te Horo (1775000 E, 5480000 N), which is unsewered. QA check 1 mixes wastewater and stormwater points, so the 74 points are almost certainly stormwater culvert ends or sumps whose levels sit below a 1 m LiDAR cell. A double datum conversion (Wellington 1953 offset about 0.44 m) is not yet ruled out. | QA check 1 in one block. | T-44 |
| 7 | Six fetched layers are never compiled: five newer KCDC flood layers and `earthworks`. Q1 checks only the District Plan flood overlay. | 3 of Q1's 288 rows lie in a newer flood layer. | T-40 |
| 8 | The 15 × 15 m platform estimate is given for parcels too small to hold one. | 1,002 parcels with under 225 m² of open ground. | T-43 |
| 9 | Parcels only partly covered by LiDAR get terrain values as if whole. | 117 parcels over 100 m² have under 80% coverage. | T-43 |
| 10 | `fetch_lidar.py` picks sheets from two corners of the window only, missing one sheet in block 1765000_5470000. | A 109,000 m² strip without LiDAR. | T-42 |
| 11 | Where a layer has no class field, the label is the layer name, so the tsunami evacuation zone is lost. | 9,428 tsunami rows, plus coastal environment, wind and part of noise. | T-40 |
| 12 | QA skips the area check in blocks without LiDAR, and the area check compares KCDC's area with itself, not with LINZ. | 93 parcels unchecked; the check is weaker than `SOURCES.md` says. | T-44 |
| 13 | Q4 says "not explained by buildings" but has no building condition, and uses one 0.08 m epoch offset where block offsets range from +0.03 to +0.16 m. Q5 counts points within 1 m, so boundary points count on both neighbours. | Q4 and Q5 wording and counts. | T-44 |
| 14 | A layer's copyright text, stored in provenance, named two council staff and gave one's email address (D-12). | One layer. **Fixed** in this change (below). | — |
| 15 | Smaller: ArcGIS paging reads `exceededTransferLimit` only at the top level and forces at least 1,000 records a page; council assets are filtered by status, not owner, so private stormwater assets may count; parcels clipped at the district boundary give shares of the clipped area; a parcel without an id would get an invented one. | Not triggered in this run, except the private assets, which are unmeasured. | T-44 |

## Fixed in this change

- Finding 14: `tile_env.scrub_copyright` withholds copyright text that contains an email, a phone extension or "by
  <Name>". The two committed copies (`docs/findings/2026-11-06-tile-provenance.json` and the `tile-results` branch)
  are corrected. The address remains in earlier commits on `main`; removing it from history would mean rewriting `main`.
  Check: `test_review.py`, which fails on the old code.

## Checked and found correct

- NZTM throughout; WFS bounding boxes in northing, easting order; LiDAR on a 1 m grid.
- Levels are NZVD2016 metres, pipe widths millimetres. Next to manholes in flat urban blocks, lowest ground sits 1.0–1.2 m
  above the invert, so there is no metre, millimetre or Wellington 1953 mix-up.
- Sun position, shadow ray direction, aspect and horizon directions.
- No duplicate parcels; block counts match `kapiti_blocks.json`. The single-tile run and the district run agree on 648
  values over 89 shared parcels.
- No violations of: ground minimum ≤ mean ≤ maximum; wastewater head = ground minimum − invert; RBL arithmetic; slope,
  roof and open-ground areas within their parents; sky view 0–100%; horizon ≤ 90°; winter sun ≤ 8 h.
- Titles: types only, no owner names. Q2 and Q3 match their descriptions.

## T-40: zone and overlay labels (fixed in code, 6 Nov 2026)

- **Cause.** The KCDC zones layer has no `ZONE` field. Its `ePlan_Zone` field holds the operative District Plan zone,
  and `PDP_ZONE` holds older names for about a third of features ("Residential", "Beach Residential", "Industrial").
  The compiler read `PDP_ZONE`. Some zone features also overlap features of the same zone, and the compiler summed the
  overlaps.
- **Fix.** `pipeline/overlays.py` labels each feature from its layer's own class field and unions overlapping features
  of a class before measuring them. The five newer flood layers and `earthworks` are compiled (83 columns). Q1 now
  excludes parcels in any KCDC flood layer, not only the District Plan overlay.
- **Checked on live data.** The reviewer's three example parcels, read again from the KCDC layers:

  | Parcel | Before | After |
  | --- | --- | --- |
  | Lot 14 DP 43617 | High Density Residential Zone 200% | High Density Residential Zone 100% |
  | Lot 27 DP 22450 | Residential 200% | General Residential Zone 100% |
  | Lot 44 DP 7203 | Residential 100%, Beach Residential 100% | General Residential Zone 100% |

- **Test tile.** On the test tile (1769000 E, 5468400 N, 535 parcels), the zone counts are unchanged and the labels now
  use operative names: 69 "Industrial" become "General Industrial Zone", and 58 "Outer Business Centre Zone" become
  "Mixed Use Zone". The query counts are Q1 16, Q2 10, Q3 18, Q4 30 and Q5 23.
- **Tests.** Three new tests in `pipeline/test_review.py` cover overlap union, the operative zone name, and class labels
  that are never the column name. Each fails on the old code.
- **One label is not in the source.** One Noise Corridor feature (9.4 km²) has no name or id in the source, so it is
  labelled "Noise Corridor (no name in source)". It is probably the road and rail corridor, but nothing in the source
  says so.
- **Rebuild.** The district results change at the next rebuild (T-45).

## T-41: query provenance (fixed in code, 6 Nov 2026)

- **Cause.** Only the parcel fetcher recorded a fetch time. The district merge renamed the sha256 to a per-block map
  that the queries never read, so every source in `inverse_queries.json` had `sha256: null` and `fetched: null`. In
  the published district results, all 23 query-level source entries have both null, and none of the 3,428 rows
  carries provenance of its own.
- **Fix.**
  - Every fetcher now records the fetch time (UTC) and sha256 for each source.
  - `pipeline/provenance.py` keeps both per block through the merge.
  - Each query row now carries `block_id` and the sha256 and fetch time of each of its sources, as fetched for its own
    block. URL, licence and first and last fetch times are given once per query.
  - Feature counts stay per block instead of being summed across overlapping fetch windows.
  - Every run prints how many rows lack a source's sha256 or fetch time.
- **Checked on live data.** The test tile was fetched again from the live sources, then compiled, merged as a
  one-block district and queried. 0 of 568 entries are missing, in both the tile output and the merged output.
- **Tests.** One new test in `pipeline/test_review.py` covers the per-block lookup, no summed feature counts, and the
  LiDAR collection link. It fails on the old code, which has no `provenance` module.
- **Size.** Per-row provenance adds about 1 KB per row, which is about 3 MB on the district's 3,428 query rows.

## T-42: window edges (fixed in code, 6 Nov 2026)

- **A second flow fault, found while fixing this one.** pysheds 0.5 left some valley-floor cells with no flow
  direction after its flat-resolution step, so flow stopped there.
  - On a 10 m district mosaic, the Ōtaki River stopped at 294 km² in its gorge and showed 60 km² near its mouth.
  - The published 1 m values are affected wherever such a cell lies on a flow path.
  - `pipeline/flow.py` replaces pysheds with priority-flood plus epsilon (Barnes, Lehman and Mulla 2014) and
    steepest-descent D8, compiled with numba, so every cell drains to an outlet.
  - A 1 km crop of the real LINZ DEM is kept as a test fixture: pysheds routes 4,636 cells to its outlet, the new code
    6,685.
- **Whole catchments.**
  - `district_flow.py` builds a 10 m mosaic once per run: LINZ's national 1 m DEM read through its overviews, with gaps
    filled from the national 8 m contour DEM. It covers the district and the Tararua catchments draining into it.
  - From that mosaic it computes the upslope area, which gives the new column `catchment_area_max_m2` for every parcel,
    including parcels without LiDAR.
  - Near their mouths the Waikanae has 148 km² and the Ōtaki 374 km², in line with their published catchments of
    about 140–150 and 350–360 km². No cell inside the district's blocks has an upslope area reaching the mosaic edge.
  - The run takes 4–5 minutes and peaks at 3 GB of memory (pysheds needed 6 GB). It is cached on GitHub for the month,
    and the cropped output is 112 MB.
- **A known limit, kept visible.** On the coastal plain north of Ōtaki, the Waitohu shows about 130 km², which is too
  large for that stream. Flow is routed in a straight line north across the plain to the mosaic edge. A DEM has no
  culverts, so road and rail embankments act as dams, and the filled area behind them spills the wrong way. This is
  noted in `SOURCES.md`; the mouths of the main rivers are unaffected.
- **Block-scale flow.**
  - `upslope_area_max_m2` is still the 1 m flow inside the block, now with `upslope_area_truncated`. The flag marks
    parcels whose upslope area reaches the window edge or a LiDAR gap over land; a gap over the sea is an outlet.
  - `flow_path_m` is now metres, with diagonal steps counted as √2. On the test tile it is a median 23% longer than the
    old cell count.
- **Wind relative height.** Ground at the parcel is now compared with the mean within ±500 m on the district mosaic,
  with the sea at 0 m, so the result no longer depends on the block's window. At the reviewer's two beach points it
  reads −3.5 and −3.4 m, against −11.3 and −15.7 m before.
- **Edges of shadows and obstruction.** LiDAR is now read 300 m beyond the fetch window, the maximum shadow length.
  On the test tile, winter sun changes by at most 0.1 h, horizon by 0.4° and obstruction by 1.6 points.
- **LiDAR sheets.** The search box comes from all four corners of the window. The old two-corner box misses part of
  block 1765000_5470000's window (test).
- **Test tile** (live, 535 parcels):
  - 86 columns, with all five queries unchanged in count.
  - The largest 1 m upslope area is 0.80 km² (was 0.19).
  - 41 parcels are flagged truncated.
  - The largest catchment is 1.03 km², and none is truncated.
- **Tests.** Five new tests in `pipeline/test_review.py`; the Ōtaki fixture, edge-only inflow, sea at 0 m and the
  four-corner search each fail on the old code.
- **On GitHub Actions** (tile workflow run 42251507841 on this branch): district flow 2 min 18 s, whole run 5.5
  minutes, same query counts as the local run, and an identical district flow sha256, so the mosaic is reproducible.

## T-43: ground-level measures (fixed in code, 7 Nov 2026)

- **Winter sun.**
  - A cell counts as sunlit at ground level only where nothing stands more than 0.5 m above it (DSM − DEM).
  - The mean and the 3-hour share are now taken over clear open ground, and a new `open_ground_clear_pct` column says
    how much of the open ground is clear.
  - My first attempt averaged ground under trees in as 0 h. That also counted every hedge, fence, shrub and vehicle,
    which cover about 15% of open ground on the test tile, so it mixed "how much ground is clear" with "how sunny the
    clear ground is". The two are now separate columns.
- **Viewpoint.** Horizon and sky view are taken from the clear open-ground cell farthest from buildings, trees and the
  boundary, so never from under a canopy.
- **Platform.** A platform estimate is given only where a whole 15 m × 15 m square lies on the parcel's open ground.
- **LiDAR coverage.** New `lidar_coverage_pct`; queries Q1, Q2 and Q4 (terrain-based) need at least 99%.
- **Test tile** (live, 535 parcels):
  - Parcels with at least half their open ground under canopy (80): winter sun 4.27 h before, measured on the canopy,
    against 1.08 h now, on the clear ground between the trees. Viewpoint sky view 19.8% before, 52.7% now.
  - Parcels with under 10% canopy (196): 4.28 h before, 3.78 h now, the difference being shade from fences and shrubs
    on the ground beside them.
  - Platform estimates: 441 parcels before, 135 now, and none with under 225 m² of open ground.
  - The tile has full LiDAR, so the query counts are unchanged; partly covered parcels are elsewhere (117 district-wide).
- **Tests.** Three new tests: a 10 m tree with the sun overhead, a viewpoint among trees, and a 12 m sliver against a
  20 m lot. They test new functions, so each fails on the old code.

## T-44: QA and query wording (fixed in code, 7 Nov 2026)

- **The Te Horo manhole block, settled.**
  - Of the in-use points with a cover level inside block 1775000–1780000 E, 5480000–5485000 N, all 38 are
    stormwater: 19 culvert outlets and 12 inlets (wingwalls), and 7 sumps. There are no wastewater points.
  - Every point's NZVD2016 and Wellington 1953 cover levels differ by the usual −0.37 m, so the levels were not
    converted twice.
  - The cause is the asset type: a culvert end's level sits in the drain, below a 1 m LiDAR cell that takes in the
    bank or road.
  - QA check 1 now compares true manholes only (node types WWMH and SWMH), reported separately for wastewater and
    stormwater. On GitHub (tile run 42297523979, the 5 km block) it gives 24 wastewater manholes at a median −0.11 m
    and 11 stormwater manholes at −0.06 m, none more than 0.5 m off. The block itself has 0 wastewater manholes; the
    24 lie where its download area reaches about 0.8 km north into Ōtaki.
- **Nearest manhole columns.** `ww_mh_*` and `sw_mh_*` now use manholes only. Before, `ww_mh_*` took any wastewater
  node with an invert, including cleaning eyes and valves; 3 of 535 parcels on the test tile change their nearest
  manhole.
- **Private assets.** The reviewer suspected private assets were included. They are not: only status `INUS` is used,
  which excludes private (`PRV`), NZTA, rail and GWRC assets.
- **Area check.**
  - The area check now compares each parcel with the LINZ parcel of the same id, and runs in every block, including
    those without LiDAR.
  - It used to compare KCDC's polygon with KCDC's own `calc_area`.
  - Te Horo block: 753 parcels, none missing from LINZ, largest difference 0.1 m².
- **Q4.**
  - The query is renamed "Ground level changed since 2021": the old name said "not explained by buildings", but it had
    no building condition. Ground surfaces exclude buildings anyway, so the change is mostly earthworks.
  - It now subtracts each block's own epoch offset, the new column `lidar_epoch_offset_block_m`, instead of one 0.08 m
    for the district.
- **Q5.** Heritage and tree points count only if they are inside or on the parcel boundary (before: within 1 m, so a
  boundary point counted on both neighbours). Each point now carries its KCDC id.
- **Paging.** A shared helper (`pipeline/arcgis.py`) pages at the layer's own record limit, reads the
  transfer-limit flag where GeoJSON puts it, and fails the run if the total differs from the server's count.
- **Ids.** A parcel without an id now stops the run instead of getting an invented one.
- **Tests.** Two new tests (paging against a server limited to 500 records, and a point 0.5 m outside a parcel). Both
  fail on the old code. The manhole split and the area check were checked on the Te Horo block on GitHub. The per-block
  offset in Q4 will be checked against each block's QA offset at the T-45 rebuild.

## T-45: district rebuild and raw-source sample check (7 Nov 2026)

The district was rebuilt with T-40 to T-44 in one GitHub Actions run (`kapiti.yml` run 42324369141, 39 minutes, all
46 blocks succeeded; the API did not report billable minutes for the run). Results are on the `kapiti-results`
branch. Before-and-after counts are in
[`2026-11-07-rebuild-before-after.json`](2026-11-07-rebuild-before-after.json).

### The reviewer's checks, before and after

| Check | Before | After |
| --- | --- | --- |
| Parcels, distinct ids | 27,614 | 27,614 |
| Columns | 77 | 89 |
| Parcels with a zone class above 100% | 1,719 | 0 |
| Overlay classes above 100% | 1 | 0 |
| Parcels carrying older zone names | 8,218 | 0 |
| Tsunami rows labelled with the layer name | 9,428 | 0 |
| Platform estimate with under 225 m² of open ground | 1,002 | 0 |
| Query rows without their sources' sha256 and fetch time | 14,387 | 0 |
| Query-level sources with a null sha256 | 23 | 0 |
| Largest 1 m upslope area | 6.3 km² | 26.4 km² (1,069 parcels flagged as reaching the window edge) |
| Largest whole-catchment area (new) | — | 353.5 km², none truncated |
| Wooded parcels (≥80% canopy): winter sun, sky view | 3.9 h, 5.7% | 1.2 h, 45.2% |
| Q4 epoch offset | 0.08 m everywhere | one per block, 0.03 to 0.13 m, each within 0.001 m of the block's QA median |
| Worst block, wastewater manholes against LiDAR | −0.49 m (Te Horo, stormwater points) | −0.11 m |

Queries: Q1 288 → 402, Q2 633 → 633, Q3 555 → 559, Q4 554 → 554 (17 in, 17 out), Q5 1,398 → 1,388.

- **Q1** gains 124 and loses 10.
  - 121 of the 124 carried only an older zone name before, as the reviewer predicted. I did not trace the other 3.
  - Of the 10 lost, 3 are now in a newer flood layer and 7 have a different nearest manhole, now that cleaning eyes and
    valves no longer count.
- **Q5** loses 10: points within 1 m but outside the parcel.

### Sample check against the raw sources

- **Method.** `pipeline/sample_check.py` does not use the pipeline's code.
  - It reads each parcel from KCDC.
  - It recomputes zone shares from the raw zone polygons.
  - It asks the KCDC and GWRC servers which flood, tsunami, coastal and liquefaction features overlap the parcel.
  - It finds the nearest wastewater manhole with its own query, and lists heritage and tree points inside the parcel.
  - It reads ground levels straight from the LINZ 2024–25 LiDAR files.
- **Parcels.** 15, chosen across block types:
  - urban Ōtaki and Paraparaumu, and the reviewer's three 200% zone examples;
  - coastal Waikanae Beach and Paekākāriki;
  - Waikanae hills, rural Te Horo and Ōtaki dunes;
  - a 2.4 km² hill block, an 11.6 m² sliver, a parcel without LiDAR and a block-edge parcel with partial LiDAR;
  - a heritage parcel and a notable-tree parcel.
- **Result.** All 15 match on all 195 checks: area, zones, seven overlay layers, nearest manhole, heritage, trees,
  and LiDAR ground mean and minimum, identical to the centimetre with the same cell counts. Run against the old
  results, the same script flags the known zone and label faults.
- **Saved.** [`2026-11-07-sample-check.json`](2026-11-07-sample-check.json).
- **Not checked.** LINZ titles and easements: the LINZ key is held only on GitHub.

### Found by the rebuild, fixed in code for the next run

- **The new area check against LINZ** reports 120 parcels more than 1 m² off, up to 547 km². These are in blocks on
  the district's edge, where KCDC's mirror clips parcels at the district boundary, already noted in `SOURCES.md`.
  QA now reports parcels smaller than LINZ separately, with examples, so a genuine mismatch is not hidden among them.
- **Q3 (4 net, 8 rows changed)** changed because of ties. These parcels lie on two pipe segments that meet, so both
  are 0.0–0.1 m away and can have different condition grades. Which one counted as nearest depended on the order the
  server sent them, which changed when paging began sorting by object id. Ties within 5 cm now go to the lowest asset
  id (test added).

### Source issues, reported rather than changed

- **Overlapping zones.** Seven parcels have zone shares summing to more than 100% because KCDC's zone layer overlaps
  zones of different types: Lot 103 DP 413488 is zoned both Open Space and High Density Residential over its whole
  area, and five lots in DP 356329 overlap Rural Lifestyle by about 1%.
- **Coastal relative heights.** 326 parcels in the coastal stainless band still read below −5 m. These are real:
  the lowest (−53 to −58 m) are Paekākāriki houses under the escarpment. Across the band, the median moved from 0.7 to
  0.8 m (correlation 0.93), so the sea bias the reviewer found affected only the beach edge.

## Correction (7 Nov 2026, from T-46)

The explanation given under T-42 for the Waitohu's 130 km² (embankments without culverts) was wrong, and was
asserted without tracing. The second review traced it. LINZ's national DEM stores the sea as a flattened surface at
about −0.6 to −1.0 m, not as no data, and `flow.py` never let a cell drain into an adjacent no-data cell. So
streams reaching the beach were routed north through the sea strip to the edge of the mosaic. See
[the second review](2026-11-07-second-review.md), finding 1; the fix is T-47.

A second correction: the two "beach points" quoted under T-42 (−3.5 and −3.4 m, against −11.3 and −15.7 m) were not
beach. Their ground of −0.6 m is the flattened sea surface in the national DEM, so those cells were sea; the
comparison showed the fill value changing, not a beach parcel.
