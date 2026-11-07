# Fresh-eyes review of the query service (T-52, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `service/` against D-12, `AGENTS.md` and `SOURCES.md`, on the
results of run 42364630209 (commit `47ace6d`; 27,614 parcels, 99 columns, 57 served in public mode). It drove the
server over MCP and directly, checked 12 parcels end to end against KCDC's public services and the LINZ elevation
bucket, and ran a mutation test of the service's tests. Its verdict: not safe to offer outside yet. The author
re-checked findings 1 to 4 before recording them.

## Findings, most serious first

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | One request can exhaust memory: `search` takes any number of conditions and DuckDB had no memory or time limit. 2,000 `contains` conditions used 2.2 GB; 6,000 (a 341 KB request) was killed for lack of memory on a 16 GB host. | Confirmed (author: 800 conditions, 418 MB) | T-53 |
| 2 | `wind_obstruction_pct` and `wind_rel_height_m`, served in public mode, are read at a viewpoint chosen using the withheld 2021 building outlines (`compile_tile.py:319`); filtering on their nulls returns exactly the parcels whose withheld horizon and sky-view values are empty (158). | Confirmed | T-53 |
| 3 | Wrong meanings served for 6 columns: the catalogue takes the first matching row, so the overlay row's `wind_*` and `ovl_*` globs captured the wind inputs and the heritage and tree lists, and the water-pipe columns shared the stormwater meaning. | Confirmed | T-53 |
| 4 | Some values not marked published, derived or modelled: the `ww_pipe_*`, `ws_pipe_*` and `sw_mh_*` rows say "published / derived", and council-published manhole ids and inverts are labelled derived. | Confirmed | T-53 |
| 5 | Public users are told to correct `dz_*` with `lidar_epoch_offset_block_m`, which is withheld because the offset uses the building mask. | Confirmed | T-54 (pipeline) |
| 6 | The water-pipe columns usually report a 20 mm service connection (18,793 parcels read 20 mm), and ties among pipes at 0 m (for example 25 mm, 375 mm and 560 mm at parcel 3745534) are settled by asset id without saying so. | Confirmed | T-54 (pipeline) |
| 7 | The gate on precomputed queries checks only the returned columns: a query filtering on a withheld column, renaming one with `AS`, or returning no rows would be served. No current leak: only Q3 is served, and it is clean. | Confirmed (crafted test) | T-53 |
| 8 | Terrain and flow columns omit `district_flow` from their sources (the sea mask and edge inflow use it), so their fit flag reads "fit" instead of its "use with caution". | Confirmed | T-53 |
| 9 | The one parcel on mirror geometry (3895556) lists only the LINZ source. | Confirmed | T-53 |
| 10 | In public mode, `columns` gives the full meaning of withheld columns, which reveals some withheld content (for example a noise-corridor class name). | Confirmed, low | T-53 |
| 11 | DuckDB errors are not caught: the client sees a generic error, but the server log gets a traceback with a data value; a huge `offset` crashes; a non-object condition raises an unhandled error. | Confirmed, low | T-53 |
| 12 | Responses are large (1.2 MB for 500 rows), and the 20 km `bbox` limit does nothing because a search without a bbox pages the whole district. | Confirmed, low | T-53 |
| 13 | The tests would pass with many errors: a mutation run left them passing with the row cap removed, fit taken from the strongest source, `buildings_2021` dropped from the roof columns' sources (serving building-derived columns publicly), every kind forced to "derived", and more. The catalogue-coverage test passes silently without results. | Confirmed | T-53 |
| 14 | Minor: pipe year and grade served as floats; the `parcels` notes cell in `SOURCES.md` is cut off; the results path is not glob-escaped (operator-set only). | Confirmed | T-53, T-54 |

## About people (D-12)

- **Public mode** serves nothing about people.
- **Internal mode** includes heritage significance text that names historical people, and one ecological site named
  after a street address.
- **For the owner to decide:** the public `titles` column holds title references, which are a direct key into LINZ's
  separately licensed records of owner names.

## Checked and found correct

- **Licence gate:** all 42 columns with a ◐ source are withheld, and refused in `columns` and in every filter op.
- **Injection:** no SQL injection; column names and ops are allow-listed, and values are parameters.
- **12 parcels against KCDC:** area, survey area, titles, intent and appellation; recomputed overlay shares (flood
  storage, river corridor, overflow path, stainless zone); and nearest wastewater pipe attributes, all matching.
- **Terrain:** ground minimum, mean and maximum on 8 parcels, exactly matching the LINZ 2024–25 DEM.
- **Q3:** its SQL re-run on the parquet gives the same 620 rows, with per-row sha256 and fetch times matching
  `provenance.json`.
- **Provenance and values:** 25 random parcels, with all 425 provenance entries and every served value matching.
- **Data:** no NaN or infinite values.

## Not checked

- **Needs LINZ LDS** (no key in the review session): titles, easements and LINZ geometry.
- **Not recomputed:** derived values from the DSM, the 2021 DEM and the district flow grid.
- **Licence statements:** the portal statements themselves were not re-verified.
- **Internal mode:** reviewed only where a finding needed it.

## T-53: service fixes (8 Nov 2026)

- **Limits** (finding 1).
  - At most 20 conditions and 1,000 `in` values a request; offset at most 100,000.
  - 500 rows with a `columns` list, 100 without.
  - DuckDB is capped at 1 GB and 2 threads, and each query at 10 seconds.
  - The 20 km `bbox` limit, which limited nothing, is replaced by checks that the box is finite and ordered.
- **Wind inputs** (finding 2). `wind_obstruction_pct` and `wind_rel_height_m` now list the building outlines (and
  the DSM) among their sources, so public mode withholds them.
- **Meanings and kinds** (findings 3, 4, 10).
  - A column's own row in `SOURCES.md` now wins over a pattern.
  - The water-pipe, stormwater and wastewater rows are split by kind, so every column is published, derived or
    modelled.
  - The shared overlay row is split into a zones row and a generic overlay row; per-layer class notes are kept as
    prose that the service does not serve. A new test found that the shared row, served for the cleared flood
    columns, described withheld layers.
  - Public mode describes withheld columns only as withheld.
- **Precomputed queries** (finding 7) are judged by every source they draw on, not only the columns they return.
- **Sources** (findings 8, 9).
  - `district_flow` added to LiDAR coverage, upslope area and flow path.
  - `title_count` lists only the parcel.
  - A parcel on mirror geometry adds `kcdc_parcels`, and every row now says its `geometry_source`.
  - Ground levels, slope and ground change do not list `district_flow`: the grid only removes sea cells from them,
    which their meaning already covers, and listing it would mark plain ground levels "use with caution".
- **Errors** (finding 11). Database errors return a plain message; non-object conditions, list values for scalar
  ops and huge offsets are refused.
- **Tests** (finding 13).
  - 8 new tests: 15 in all, with all passing on the published results.
  - The reviewer's mutations, plus two more, are all caught now: no row cap, no all-columns cap, fit from the
    strongest source, buildings dropped from roof or wind sources, offset ignored, no condition cap, the old query
    gate, kinds forced to "derived", withheld columns described.
  - Checks needing the published results print SKIPPED rather than passing silently; the district workflow sets
    `LANDQ_RESULTS`.
- **Left for T-54** (pipeline, needs a rebuild):
  - the epoch offset computed without the building outlines, so the `dz_*` correction can be served (the test
    names this as its one known exception);
  - water pipes excluding 20 mm service connections, with a tie rule and tied ids;
  - integer pipe year and grade.

## T-54 and T-55: pipeline fixes and title references (8 Nov 2026)

- **Epoch offset** (finding 5). `lidar_epoch_offset_block_m` now uses flat, clear ground from LiDAR alone (DSM within
  0.5 m of the DEM already excludes roofs), without the 2021 building outlines. So it is licence-cleared, and public
  users can correct `dz_*`. Block offsets now run from +0.03 to +0.11 m across 20 blocks.
- **Water mains** (finding 6).
  - The nearest water pipe is now the nearest main: KCDC types `RETI`, `RIDE` or `TRNK`, carrying treated water.
    Before, it was usually a 20 mm service connection: 18,793 parcels read 20 mm; now 47 do.
  - Ties go to the largest main, with all ids in the new `ws_pipe_tied_ids`, and the new `ws_pipe_type` gives the type.
  - Parcel 3745534 now reads the 560 mm trunk main, with its four tied pipes listed.
  - 3,152 parcels, mostly rural, have no main within 150 m.
- **Whole numbers.** Pipe year and grade are integers in the compiler (checked on a tile). In the published results
  they were still stored as decimals, because merging blocks with empty values turns the column decimal again, so the
  compiler now stores them as nullable integers and the service presents them as whole numbers meanwhile (test added).
- **Titles** (T-55, D-15). Public mode withholds `titles`; title type and count are still served.
- **The run.**
  - The rebuild (run 42371100493) built all 46 blocks, then the service check stopped the merge before publishing: a
    `SOURCES.md` note I had added after running the tests locally named the withheld `titles` column in the served
    `unit_id` description. The guard worked as intended.
  - After the fix, `kapiti.yml` merged those blocks again without recomputing them (new `reuse_blocks_from` input,
    run 42374135961, about 3 minutes), so the fix cost a few cents instead of a second rebuild.
