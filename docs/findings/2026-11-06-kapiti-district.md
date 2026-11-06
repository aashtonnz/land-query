# Kāpiti Coast district compile: findings (6 Nov 2026)

T-21. The whole district compiled from live public sources in one GitHub Actions run (`kapiti.yml`, run 42174240520).
Results: the [`kapiti-results`](https://github.com/aashtonnz/land-query/tree/kapiti-results/results) branch (`units.parquet`,
`inverse_queries.json`, `qa_summary.json`, `blocks.json`, `summary.md`).

## How it ran

- 46 blocks of 5 km × 5 km. Each parcel belongs to the block holding its representative point and is computed whole: the
  fetch window grows to cover the block's parcels, capped at 1 km beyond the block.
- 27,614 parcels, matching the KCDC cadastral layer's count for the district exactly; no parcel appears twice. 61 columns.
- 18.5 minutes wall time, 8 blocks at a time; the densest block (6,345 parcels, Paraparaumu) took 7 minutes. 160 billable
  Actions minutes per full run, against 2,000 free a month for a private repository.
- Titles joined for 26,818 parcels (97%); the rest are reserves, roads-to-be and other parcels without a title reference.

## Quality checks (every block)

| Check | Result |
| --- | --- |
| Council manhole cover levels minus LiDAR ground | 17,432 manholes; median of block medians −0.10 m. One block (inland Waikanae, 1775000 E 5480000 N) has a median of −0.49 m with half its 74 manholes more than 0.5 m off: unexplained, flagged for T-39 |
| Council 2021 building ground heights minus LiDAR | 68,033 buildings; median of block medians −0.08 m; worst block −0.26 m |
| LiDAR 2024–25 minus 2021 on flat open ground | 4.2 million cells; median of block medians +0.073 m (single tile: +0.08 m); worst block +0.16 m |
| Parcel area against LINZ `calc_area` | 97 of 27,521 differ by more than 1 m². These are rural sections: the KCDC mirror clips parcels at the district boundary (Section 5 SO 495075 is 615 km² in LINZ, 68 km² in the mirror), and some legacy sections are split into fragments |
| Parcels without LiDAR | 544 (2%): 13 blocks outside the LiDAR surveys (Kapiti Island, Akatarawa and Tararua foothills) and the foothill edges of others. Terrain columns are empty for these, not estimated |
| Parcels partly outside their fetch window | 39 very large rural parcels; overlap and terrain values cover only the share shown in `coverage_pct` |

## Inverse queries, whole district

Over the 27,236 parcels that are fully covered and at least 20 m²:

| Query | Parcels |
| --- | --- |
| Q1 Gravity-serviceable infill candidates (residential, ≥800 m², <25% built, flat, no flood overlay, sewer invert ≥1 m below ground within 30 m) | 288 (276 freehold; 192 General Residential, 92 High Density) |
| Q2 Recommended floor level more than 1 m above mean ground | 633 |
| Q3 Nearest sewer before 1980 and condition grade 4–5 | 555 |
| Q4 Ground change since 2021 | 554 |
| Q5 Heritage, notable tree or ecological site | 1,398 |

**The change signal holds district-wide.** 298 of the 554 Q4 parcels (54%) are on survey plans from DP 550000 onward,
against 5.8% of all parcels. Most ground change is new subdivision earthworks. The rest are the candidates for T-29.

## What changed in the pipeline

- Parcels are assigned by representative point and computed whole. On the old single tile, five parcels near the edge
  had picked a farther manhole because the nearer one lay just outside the tile; that is fixed.
- Terrain is computed in a small window per parcel (a 1 km tile went from 13 s to 10 s; the densest block takes about 2 minutes).
- New columns: `block_id`, `coverage_pct` (replaces `in_tile_pct`), `lidar_cells`.
- Blocks outside the LiDAR surveys are recorded as "no coverage", not failures.

## For the fresh-eyes review (T-39)

- The inland Waikanae manhole block above.
- Q5 counts every heritage or tree point within 1 m; check it isn't picking up road-reserve features on boundaries.
- `zones` and overlay percentages for parcels clipped at the district boundary are shares of the clipped area.
