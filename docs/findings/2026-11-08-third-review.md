# Third fresh-eyes review (T-57, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed everything changed since the second review was recorded
(`88c6b5f..4b86d7a`: T-47 to T-56) against the published results (run 42374135961, blocks from run 42371100493).

- **Rebuild.** It rebuilt coastal block 1765000_5470000 from live sources, including its own district grid, which
  had the same sha256. All 101 columns for its 5,816 parcels match the published values, apart from float jitter.
- **Independent checks.** 16 parcels' terrain and catchment, 13 parcels' water and wastewater columns, and the Ōtaki
  and Waitohu catchments, checked independently: all match.
- **Confirmation.** The author re-checked finding 1 before recording it: 470 parcels.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | Parcels with no LiDAR, in blocks that have LiDAR, read 0 instead of empty for `canopy_gt3m_open_pct` and `open_ground_slope_lt5_m2` (470 parcels, mostly foothills); 5 islands show LiDAR coverage above 0 with no cells; the new `dz_2021_2025_clear_pct`, which is served publicly, would read 0 for the same parcels and for 94 parcels with 2025 but no 2021 LiDAR. Invented values (D-12). | Confirmed, serious | T-59 |
| 2 | Parcels LINZ has but KCDC's mirror lacks are dropped and not counted: membership comes only from the mirror, and QA compares only ids the mirror has. The one parcel on mirror geometry (3895556) looks retired by LINZ, so its replacements may be missing. | Suspected, serious | T-59 |
| 3 | Failed sources, and a LINZ fetch falling back to the mirror, don't stop a run publishing; a failed easement fetch would read as 0 easements. | Confirmed (code path), minor now | T-59 |
| 4 | `RUN.txt` names the merge run's commit, not the commit the reused blocks were compiled at (b6d5a01), so the published pipe columns are still decimals and the clear-ground columns are absent although T-54 and T-56 are merged. | Confirmed, minor | T-59 |
| 5 | The catalogue's source lists for ground, slope, LiDAR cells, ground change and wastewater head omit the district grid, which masks the sea before they are computed. | Confirmed, minor | T-59 |
| 6 | Service: the 20 km bbox limit is promised but not enforced; listing every column bypasses the 100-row cap; a non-numeric `min_pct` raises an uncaught error; concurrent requests share one database connection, and one request's timer can interrupt another's query. | Confirmed (concurrency suspected), minor | T-59 |
| 7 | Tests: 13 of 22 mutants survived, including "any no-data neighbour is an outlet" (a test named for that rule doesn't test it), tie tolerance 0 or 50 m, a sea mask returning no sea, `extend_sea` growing over all low land, dropping `buildings_2021` from sun and horizon sources, and titles allowed in a precomputed query's rows. No test covers `compile_tile.py`. | Confirmed, minor | T-59 |
| 8 | The sea counts as 0 m for flow, but the 1 m DEM has land below 0 m beside it (1,824 cells in one block), which then cannot drain to the sea; in one block 2 parcels' upslope area changes by more than 20% (Lot 1 DP 29696: 0.25 → 6.3 km²). | Confirmed, minor | T-59 |
| 9 | The weekly source check reports an unreadable source only in the week it breaks, and fingerprints the national DEM catalogues, which change whenever any survey in New Zealand is added (false alarms). | Confirmed, minor | T-59 |
| 10 | `SOURCES.md`: epoch offsets now reach +0.114 m, not +0.16; the water-main filter is by pipe type and keeps 25 reticulation mains of 20 mm. | Confirmed, minor | T-59 |

## Not checked

- **Needs the LINZ key:** LINZ geometry where it differs from the mirror (88 parcels), titles, easements, and how
  many LINZ parcels the mirror lacks.
- **Other blocks:** no foothills or second block was rebuilt.
- **DSM measures** were reproduced only with the project's own code.

## T-59: fixes (8 Nov 2026)

- **No-LiDAR values** (1). `measures.lidar_parcel_stats` gives coverage 0 and leaves canopy, flat open ground and the
  clear-ground change empty when a parcel has no LiDAR cells. Clear-ground share counts only cells with both
  surveys. Test added.
- **Parcels the mirror lacks** (2). Each block now counts LINZ parcels inside it and inside the district (from KCDC's
  boundary line) that the mirror lacks, with up to 20 examples, in provenance and the QA summary
  (`linz_not_in_mirror`). They are reported, not yet compiled; the next run gives the district-wide count.
- **Failed sources** (3). A LINZ error now marks the parcels source failed, and `check_complete.py` refuses to
  publish a run with any failed source. Test added.
- **Commits** (4). Each block records the commit it was compiled at, and `RUN.txt` names both the merge commit and the
  block commits.
- **Sources** (5). Ground levels, slope, ground change and wastewater head list a new `sea_mask` source, a ✅ row in
  the register whose provenance is the district grid. Listing the grid itself would have marked plain ground levels
  "use with caution", the catchment model's flag.
- **Service** (6). The 20 km bbox limit is enforced; more than 20 requested columns count as a full row for the cap;
  a non-numeric `min_pct` gives a plain error; queries run one at a time, so a timer cannot interrupt another
  request's query. Tests added.
- **Tests** (7).
  - The fill-rule test now tests its rule: a pit beside a higher survey gap fills and overflows downhill.
  - New tests cover 5 cm ties, the district sea mask, a low beach that must stay land, titles in a precomputed query,
    and the sun and horizon sources.
  - A new check fails the publish if any column defined in `SOURCES.md` is missing from the results. I added it after
    a local compile crashed on a slip of mine: one edit had dropped `ground_min_m` and `ground_mean_m` from the
    compiler, and no test would have caught it. It also shows the published results lack the clear-ground columns
    (finding 4).
  - Of the reviewer's surviving mutants re-run here, all 11 are now caught.
- **Sea level for flow** (8). Sea cells now sit below any land for flow (`flow.SEA_M`), so coastal land below 0 m drains
  into the sea.
- **Source check** (9). Unreadable sources are flagged every week; the national DEM catalogues are recorded but never
  flagged.
- **Wording** (10). `SOURCES.md` corrected for the offset range and the water-main filter.

The district rebuild (about US$2) follows. Then, under fresh-eyes review 1.1, a fourth review, because finding 1 was
serious.
