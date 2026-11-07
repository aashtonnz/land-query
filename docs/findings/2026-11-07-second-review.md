# Second fresh-eyes review (T-46, 7 Nov 2026)

A new reviewer, briefed with the repository only and told not to read these findings until it had formed its own,
reviewed the T-40 to T-45 changes and the rebuilt district results (run 42324369141). Its report follows unedited
apart from this header; scratch paths refer to the review session. The author checked findings 1 and 3 before
recording them. Fixes are T-47 to T-50 on the board.


I worked from the code, the raw public sources and origin/kapiti-results (run 42324369141). I read docs/findings
only after forming the findings. I edited no tracked file, made no commit or push, started no workflow and contacted
no one. Scratch directory: /tmp/claude-0/-home-user-land-query/d8793094-64c4-5b1a-ade6-49561640d599/scratchpad/t46
(chk/ holds the scripts, res/ the results, dl/ the downloads, flow/ my rebuild of the district mosaic).

## 1. The district flow carries rivers through the sea: this is the Waitohu "130 km²" (CONFIRMED)

What is wrong:
- pipeline/flow.py:50-59 (`_receivers`): a cell next to no data never drains into it. It drains sideways to its
  steepest lower land neighbour, so it is an outlet only when it is a local minimum. The docstring says such cells
  are outlets.
- pipeline/district_flow.py:84-90: LINZ's national 1 m DEM holds a hydro-flattened sea surface as real values, not
  no data. It is -0.56 m off Ōtaki (Kāpiti 2024-25 survey, BN32) and -1.005 m north of 1780000 E (BN33). Only values
  at or below -100 are masked, so 71.7 km² of sea counts as land. The fill drains this strip to its lowest outlet, the
  mosaic's north edge at 5,510,000 N.

Evidence:
- I rebuilt the mosaic with district_flow.py. It reproduces the published catchment_area_max_m2 for 27,608 of
  27,611 parcels.
- chk/trace.py follows the flow downstream from the Waitohu/Mangapouri stream (1781425, 5488075; 36.9 km²):
  - it reaches the beach at about 5,489,000 N (41.7 km²);
  - it runs north through sea cells at -0.57 m, then -1.01 m;
  - a separate 78.2 km² stream joins at (1780795, 5493455);
  - it reaches 130.2 km² at (1780895, 5493975);
  - it ends at the raster edge (1785835, 5509995) with 428.9 km².
- chk/upstream.py shows the two streams' catchments are separate: 37.8 km² and 78.2 km².
- BN33.tiff samples -1.005 at (1782755, 5499105), where the 8 m DEM has no data. The Kāpiti 2024-25 tile
  BN32_10000_0405 samples -0.56 at (1779255, 5490015), where the 2021 survey has no data.
- chk/test_proposed.py builds a slope down to a NaN sea column. One beach cell collects 450 cells against 9 expected,
  so the test FAILS on the current code.

How much it affects:
- The raster is wrong along the coast north of Ōtaki, and the SOURCES.md explanation ("embankments without
  culverts") does not describe what the code does.
- Parcels whose published value comes from a sea-strip cell (chk/strip.py):
  - 3864724 (Section 99 Block II Paekakariki SD): 29.72 km² published, against 0.042 km² on its own land;
  - 3 parcels at the Waikanae mouth, which may be the real estuary.
- 56 parcels touch the strip.
- The 1 m block flow (compile_tile.py:171) uses the same receivers on the same flattened sea. Beachfront parcels
  7374735 (18.5 km²) and 7355033 (13.9 km²), both with ground_min -0.56, are SUSPECTED.

Suggested fix:
- Make cells next to no data, and edge cells, outlets.
- Mask the flattened sea, for example where the 8 m DEM has no data, or at or below 0 m and connected to the sea,
  keeping cells inside mapped river corridors.

Checks that fail now and should pass once fixed:
- the beach test in chk/test_proposed.py;
- the cell at (1780895, 5493975) should be about 80 km² or less;
- no sea cell outside a river corridor should have an upslope area above 1 km².

## 2. The published results predate the tie fix, and the fix picks arbitrarily (CONFIRMED)

What is wrong:
- Run 42324369141 used head_sha f7c86cd (from gh api). The tie-break (overlays.py:39-47, called by
  compile_tile.py:184-186) and the QA split arrived later, in 4240c77; qa_summary.json lacks
  `smaller_than_linz_gt_1`.
- On main, a tie goes to the lowest asset_id. For two manholes inside one parcel, that choice has no physical
  meaning.

Evidence (chk/ties.py, over all 5,897 WWMH manholes with an invert and 8,144 in-use pipes):
- 437 parcels have tied manholes; 239 published a different one from the current rule.
- 3,999 parcels have tied pipes; 2,087 published a different one.
- 789 parcels' tied pipes differ in year or condition, 30 of them in Q3.
- 239 parcels' tied manholes differ in invert, 6 of them in Q1.
- Examples:
  - 6627870 published KWWN003040 (invert 2.40), but KWWN003039 (2.71) is also at 0 m;
  - 7260303 published KWWN001203 (38.39), not KWWN001202 (39.58);
  - 4036933 has tied inverts of -1.36 and 2.79.

Suggested fix:
- Rebuild before T-36.
- Return all tied assets, or for Q1 the deepest invert among them.
- Record the commit SHA in RUN.txt and check it.

## 3. LiDAR provenance in query output has no URL and no licence (CONFIRMED)

What is wrong: provenance.py:31 takes url and licence from the first block it meets. For LiDAR that is block
1755000_5470000 (Kapiti Island), which has no coverage.

Evidence:
- In res/inverse_queries.json, dem_2025 shows `url: null, licence: null` in Q1, Q2 and Q4, and dem_2021 the same in Q4.
- Reproduced with merge_sources: with the no-coverage block first, url and licence come out null; in the reverse
  order they are right.

How much it affects: 1,589 rows (Q1 402, Q2 633, Q4 554). This breaks D-12. The existing test passes only because it
puts the covered block first.

Suggested fix: fill url and licence from the first block that has them, and count only covered blocks. Test with the
no-coverage block first.

## 4. catchment_area_max_m2 takes any 10 m cell touching the parcel (CONFIRMED)

What is wrong: compile_tile.py:119 uses `all_touched=True`, but SOURCES.md says "draining through the parcel".

Evidence (chk/touch.py): 513 parcels have a value of at least 1 km² that is more than twice the best cell whose centre
is in the parcel. 92 of them are at or above 10 km², and 331 lie in no river or stream corridor. Examples:

| Parcel | Area | Published | Best cell centred in parcel |
| --- | --- | --- | --- |
| 3883291 | 2,592 m² | 138.1 km² | 0.000 km² |
| 3765680 | | 320.9 km² | 0.40 km² |
| 3998656 (no corridor) | | 121.1 km² | 0.20 km² |

Suggested fix: use cells whose centre is in the parcel, or cells overlapping it by half or more. Check: 3883291 should
read under 1 km².

## 5. The 7 parcels with zone shares over 100% (CONFIRMED)

What is wrong: overlays.py:25-31 unions overlaps within a class only. KCDC's layer stacks polygons of different
zones:
- 7260303 (a reserve): Open Space polygon 1606 sits wholly on High Density Residential polygon 1186, giving 100% + 100%.
- 6627870: Open Space 1604 at 100% and Natural Open Space 1190 at 99.9%.
- Lots 12-17 DP 356329 and Lot 17 DP 357567: sliver overlaps of 0.4-1.2% between Rural Lifestyle 823 and General
  Residential 1205.
- 0.0% shares are also emitted (3751121).

How much it affects: 7 parcels. A reserve can pass Q1's zone test.

Suggested fix: add an overlap flag, or give the smaller polygon precedence. Check: the shares for 7260303 sum to
100 ± 0.5, or the flag is set.

## 6. kapiti.yml can overwrite the district results with a partial run (CONFIRMED by reading)

What is wrong:
- The `only` input (kapiti.yml:29-34) is followed by `rm -rf results` and a push (:127-129).
- `fail-fast: false` (:68) with `if: always()` (:109) merges whatever blocks succeeded, and nothing checks that all
  46 are present.

Suggested fix: refuse to push when `only` is set or when the block count differs from kapiti_blocks.json.

## 7. QA treats every parcel smaller than LINZ as clipped (CONFIRMED in code; effect SUSPECTED)

What is wrong: qa.py:40-41 hides every parcel more than 1 m² smaller than LINZ without checking that it touches the
district boundary. An example is inland Te Horo (block 1775000_5480000, 2 parcels off by up to 2.98 m²); I could not
check them because LINZ needs the key.

Suggested fix: count a parcel as clipped only if it lies near the boundary. Check: a fixture with an inland parcel
shrunk by 5 m² must be reported.

## 8. Q3's year cutoff sits on a placeholder-looking spike (SUSPECTED)

Evidence: among in-use pipes, 1,934 have install year 1980 and 1,347 have 1979, against 216 or fewer for any other
year except 2023. 395 of Q3's 559 rows are 1979.

Suggested fix: state the caveat in the column note and in Q3's question, or test whether Q3 is stable when the cutoff
moves.

## 9. Smaller points

- **sha256 cannot be checked by anyone.** It is taken over the pipeline's re-serialised JSON or decoded arrays, and
  the raw data is not kept (fetch_tile.py:77-80, fetch_lidar.py:54, district_flow.py:115).
- **lidar_coverage_pct** (compile_tile.py:221) is relative only to the part of the parcel inside the window, for 39
  parcels.
- **Truncation flags.** The gap test (compile_tile.py:164-170) treats the flattened sea as land, so it sets
  `upslope_area_truncated` without need.
- **wind_rel_height_m** counts the flattened sea at -0.56 or -1.0 m instead of 0 m; the effect is small.
- **Noise corridor labels.** 1,839 parcels say "no name in source", against SOURCES.md's "boundary id".
- **Nearest-asset radius.** Candidates come from the bounding box of a 150 m buffer, so a "nearest" asset can be up
  to about 212 m away.
- **Weak tests:**
  - the flow tests never test cells next to no data;
  - the provenance test never puts a no-coverage block first;
  - the wind test covers only `mean_ground`;
  - inverse_queries' "missing 0" check ignores url and licence.

## Sample check (independent code: chk/indep.py, chk/compare.py)

I checked 21 parcels:
- Block types: urban Paraparaumu, Waikanae, Ōtaki, Paekākāriki, Waikanae North, rural, a foothills block without LiDAR,
  Kapiti Island, and partial LiDAR.
- Query rows: Q1, Q2, Q3 and Q4.
- Special cases: the double-zoned parcels, and parcels on the Waitohu, Mangapouri and Ōtaki.
- Ids: 3820954, 3955856, 3901744, 7260303, 6627870, 6808744, 8639775, 3920427, 8394633, 3850229, 6919697, 3784118,
  3749794, 3818227, 3751121, 3932262, 4011329, 3965302, 4024437, 3750528, 4006820.

What I compared, against KCDC cadastre, zones, flood overlay, wastewater nodes and pipes, RBL points, and the LINZ
2024-25 and 2021 1 m DEMs:
- area, LiDAR cells, ground min, mean and max, dz mean and abs-max;
- zones and the flood overlay;
- nearest manhole id, distance and invert;
- nearest pipe distance and its tie set;
- RBL count and max;
- catchment.

Result: 316 checks, 4 mismatches. All 4 are the manhole ties in finding 2.

## Checked and correct

- **Flow mechanics.** The priority-flood fill uses nextafter, the accumulation order is valid, units are m², and
  step lengths are 1 or √2.
- **D8 and windows.** The D8 tables are right, the raster windows have no off-by-one, and everything is in EPSG:2193.
  The WFS axis order is right, and the LiDAR sheet search uses all four corners.
- **Sun and surface geometry:** NOAA sun position, NZST offsets, shadow direction, the aspect convention, horizon
  direction indices, and the platform erosion.
- **Mean ground within ±500 m:** a 101-cell window at 10 m.
- **Fetching:** ArcGIS paging with the count check, and layer field names that match the live schemas.
- **Provenance and merge.** sha256 and fetch time are present on every row. 46 of 46 blocks merged, with no failed
  sources and no duplicates.
- **Queries:** the SQL for Q2, Q4 and Q5 matches the question.
- **D-12 output:** OWNER fields are categories, not names, and are not output. Copyright scrubbing works.
- **Tests:** all 20 existing tests pass.

## Not checked

- **LINZ titles, easements and the area check against LINZ.** These need the LINZ key, which is held only as a
  GitHub secret.
- **The 1 m measures.** Winter sun, roof solar, horizon and sky view, obstruction, platform, and the 1 m flow: I
  reviewed the code only.
- **The true Waitohu catchment.** I had no hydrology layer to check it against.
- **GitHub caching.** I did not start any workflow.

## Comparison with docs/findings (read afterwards)

- **Waitohu.** The previous review blames embankments; the actual mechanism is routing through the flattened sea plus
  coast cells that never drain into the sea.
- **Ties.** The previous review called them "fixed for the next run" and put the effect at "Q3 4 net". Against the
  current rule I find far more: 2,087 pipe and 239 manhole picks, 30 Q3 rows and 6 Q1 rows.
- **Overlapping zones.** Recorded as a source issue ("reported"), but nothing in the code flags them.
- **New in this review:** findings 3, 4, 6, 7 and 8.

## T-47: flow at the coast (fixed in code, 7 Nov 2026)

- **Drainage into no data.** `flow.py` now gives no-data cells an elevation: the sea at 0 m, or the 10 m ground
  where the 1 m survey has a gap over land. A cell drains into them when that is its steepest drop, and the flow
  leaves the raster there.
  - A cell beside a higher survey gap is not an outlet (test).
  - The reviewer's beach test (a coast sloping south, sea to the west) gives 450 cells at one beach cell on the old
    code. On the new code each row reaches the sea at its own beach cell.
- **The flattened sea.**
  - `district_flow.py` masks as sea the cells with no value in the 8 m contour DEM and no higher than 0.5 m. Checked
    at six points: the 8 m DEM has no data exactly where the 1 m DEM reads −0.56 or −1.005.
  - The compiler masks the same sea in the block's 1 m LiDAR, using the district grid, and counts masked sea cells as
    covered for `lidar_coverage_pct`.
  - River beds below sea level, such as the Ōtaki mouth, have 8 m values and stay land.
- **Catchment cells.** `catchment_area_max_m2` now uses 10 m cells whose centre is in the parcel, or the cell
  holding a parcel too small to contain a centre.
- **Checked on a local rebuild of the district grid:**
  - The Waitohu stream ends at the coast at 1779215, 5489105 with 41.7 km², the reviewer's traced figure. The cell
    that read 130 km² is masked sea.
  - Waikanae 145.8 km² and Ōtaki 373.1 km² near their mouths, as before.
  - Parcel 3864724 (Paekākāriki): 0.042 km², was 29.7. Parcel 3883291: 0.001 km², was 138.1.
- **Test tiles.**
  - Paraparaumu Beach (1766000, 5469000; 355 parcels): 753,130 sea cells masked in the LiDAR window. Parcel values
    are identical to the old code there, because the flattened sea lies seaward of the parcels, so the reviewer's
    suspected 1 m effect does not appear on that tile.
  - Inland test tile: catchment changes for 441 of 535 parcels under the cell-centre rule.

## T-48: provenance and publishing safety (fixed in code, 7 Nov 2026)

- **Provenance.** `merge_sources` takes URL and licence from the first block that has them. Before, it took them from
  the first block met, which for LiDAR is Kapiti Island's block with no coverage. The new test puts that block first
  and fails on the old code. Every query run also prints how many sources lack a URL or licence.
- **Partial runs.** `kapiti.yml`'s merge job runs `pipeline/check_complete.py` before publishing. It refuses when
  the run was limited with `only`, when it planned fewer than the district's 46 blocks, or when a planned block has no
  results; the push step is then skipped.
  - Tried on GitHub with `only` set to one block (run 42353181964): the merge job stopped with "run limited to
    blocks" and "planned 1 blocks of the district's 46".
  - The `kapiti-results` branch kept run 42324369141.
- **Run record.** `RUN.txt` now records the commit the results were built from.
