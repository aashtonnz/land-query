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
