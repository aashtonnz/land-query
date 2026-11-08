# Fourth fresh-eyes review (T-61, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed everything changed since the third review was recorded
(`4b86d7a..aa1d01a`: T-59 and T-60) against the published results (run 42434764666, a patch of run 42431175935).
It checked 13 parcels end to end against KCDC and LiDAR, including no-LiDAR, partial-LiDAR, coastal and patched-block
parcels, and ran a mutation test. The author re-checked finding 1 before recording it: 349 parcels.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | 349 published parcels have their representative point outside the district, and 319 lie entirely outside, including 22 Porirua parcels at Pukerua Bay and 262 north of Ōtaki. KCDC's mirror is not clipped to the district (D-13 and `SOURCES.md` assumed it was), and the pipeline never tested membership. 288 have no zone, so their empty overlays would read as "no hazard" where KCDC simply has no data (D-12). They appear in Q5 (38 rows) and Q4 (1). The reviewer's district outline (731.3 km² of land) agrees with KCDC's 2025 ward polygons to 0.2 km². | Confirmed, serious | T-62 |
| 2 | The published `linz_not_in_mirror` (1,246) and its examples are the wrong ones from before the district outline was fixed; only the weekly check (72) was corrected. Per block, a LINZ parcel in the mirror but assigned to a neighbouring block would count as missing. | Confirmed, minor | T-62 |
| 3 | The LiDAR item lookup (`items_for`) has no retry or status check, and a malformed catalogue response raises an error that is caught as "no coverage", so a block could publish with empty terrain. The T-60 retry fix covered the downloads, which the failing block never reached. | Code path confirmed, cause suspected | T-62 |
| 4 | The service's `about()` runs outside the query lock; under concurrent calls 143 of 180 failed. | Confirmed, minor | T-62 |
| 5 | New tests that pass on wrong code: tie tolerance 0.5 m, sea-mask threshold 5 m, `SEA_M = 0`, a duplicated-column cap test; a test and `SOURCES.md` disagree on whether an all-sea parcel counts as covered. | Confirmed, minor | T-62 |
| 6 | `lidar_coverage_pct` rounds to 0.0 on 2 parcels that have LiDAR cells and terrain values. | Confirmed, minor | T-62 |
| 7 | Smaller: `sea_mask` missing from some columns built on the masked DEM; the parcels `ok` flag stays true if LINZ returns nothing; patch runs don't check that blocks share one district-flow grid; `SOURCES.md` says 544 parcels without terrain (543); the source check drops LINZ layers silently if the key is missing. | Confirmed, minor | T-62 |

The patch run itself was consistent: the two commits differ only in LiDAR download retries and the workflow; the
recomputed block has no LiDAR, and all 46 blocks used the same district-flow grid.

## About people

Nothing new; the reviewer found nothing about people in public mode.

## Not checked

- **Needs the LINZ key:** LINZ geometry and fields, titles, and the 72-parcel gap.
- **Actions logs:** the original LiDAR failure was not confirmed from them.
- **Not recomputed:** flow, sun, horizon, roof and earthworks values.

## T-62: fixes (8 Nov 2026)

- **District membership** (1).
  - `fetch_parcels_kcdc.py` builds the district outline on every run, from KCDC's boundary line closed at sea, and
    keeps a parcel only if its representative point lies inside it.
  - Each kept parcel gets `district_share_pct`; the dropped ones are counted, with examples, in provenance and the QA
    summary (`outside_district_dropped`).
  - Checked on a 2 km tile at Pukerua Bay: the four Porirua lots (DP 33618, DP 87334) are dropped.
  - Three blocks hold no parcels inside the district and are removed from `kapiti_blocks.json` (46 → 43). The district
    has 27,265 parcels, not 27,614.
  - The compiler now stops with a clear message on a block with no parcels.
- **Mirror gap** (2). A LINZ parcel counts as missing only if no mirror feature in the block query has its id; the
  next run republishes the count.
- **LiDAR lookup** (3). Catalogue requests retry and check their status, and "no coverage" is its own exception, so a
  malformed response fails the block instead of passing as no LiDAR.
- **Lock** (4). `about()` runs under the query lock (test with mixed concurrent calls).
- **Tests** (5). New or tightened: ties (6 cm is not a tie), the sea-mask threshold (0.6 m is land), coastal land
  below sea level drains to the sea, the wide-column cap with distinct columns, and patch runs refusing mixed
  district-flow grids. All six mutants of the reviewer's kind are caught, after one more test was added for the
  last.
- **Coverage** (6). At least 0.1 when a parcel has any LiDAR cells.
- **Smaller points** (7).
  - `sea_mask` is added automatically to every column built on LiDAR.
  - The parcels source is marked failed if the key is set and LINZ returns none of the block's parcels.
  - `check_complete.py` refuses blocks built on different district-flow grids.
  - `SOURCES.md` now says 543.
  - The source check flags a missing LINZ key every week.
- **`SOURCES.md` corrected:** the mirror is not clipped to the district.
