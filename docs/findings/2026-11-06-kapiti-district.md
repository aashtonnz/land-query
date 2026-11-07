# Kāpiti Coast district compile: findings (6 Nov 2026)

> Superseded in part: the fresh-eyes review (T-39) found faults in these results, and the district was rebuilt on
> 7 Nov 2026. Current counts are in [the review](2026-11-06-fresh-eyes-review.md#t-45-district-rebuild-and-raw-source-sample-check-7-nov-2026); for example, Q1 is now 402 parcels, not 288.

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
| Council manhole cover levels minus LiDAR ground | 17,432 manholes; median of block medians −0.10 m. One block (Te Horo, 1775000 E 5480000 N; first described here as inland Waikanae) has a median of −0.49 m with half its 74 manholes more than 0.5 m off: the block is unsewered and the check mixes in stormwater points ([T-39](2026-11-06-fresh-eyes-review.md)) |
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

- The Te Horo manhole block above (first described as inland Waikanae).
- Q5 counts every heritage or tree point within 1 m; check it isn't picking up road-reserve features on boundaries.
- `zones` and overlay percentages for parcels clipped at the district boundary are shares of the clipped area.

## Computed measures (T-37, run 42179435755)

16 new columns per parcel (77 in all): winter sun on open ground, roof pitch, flat and north-facing roof area, relative
roof solar exposure, overland flow (upslope area and flow-path length), levelling cut and fill, a 15 m platform estimate,
wind exposure inputs, horizon and sky view. Definitions and kinds (derived or modelled) are in [`SOURCES.md`](../../SOURCES.md).

The district run now takes 39 minutes and 308 billable Actions minutes (the densest block 15 minutes, 4.6 GB peak memory), so a full
rebuild uses about 15% of the free monthly allowance.

**Checks**

| Measure | Check | Result |
| --- | --- | --- |
| Sun position | Solstice noon altitudes for Wellington (known answer) | Within 0.3° |
| Shadows | 10 m wall, sun at 45° (known answer) | 10 m shadow, exact |
| Horizon | Flat ground; wall 10 m high at 10 m (known answers) | 0° and 45° |
| Overland flow | Tilted plane (known answer); KCDC flood hazard areas (independent) | Exact on the plane. District-wide, parcels with a modelled flow path are in a KCDC flood hazard area 1.14 times as often as all parcels: weak, as expected from a surface model that cannot see stormwater pipes |
| Overland flow and floor levels | KCDC recommended building levels (independent) | Parcels whose floor level must sit more than 1 m above ground are 1.66 times as likely to carry a modelled flow path |
| Roof surface | KCDC 2021 photogrammetric building heights (independent) | 27,375 buildings; median of block medians −0.54 m (all blocks with more than two buildings between −0.77 and −0.44 m) |
| Wind exposure class | KCDC very-high-wind and coastal corrosion zones (independent) | **Failed.** Low surrounding obstruction is half as common inside KCDC's wind zones as outside (lift 0.50 and 0.46). Coastal exposure in Kāpiti comes from open sea and westerlies, which an obstruction-and-height rule misses. The class is withheld; its two inputs are kept as derived values |

The earlier query counts are unchanged, as expected: the measures are new columns, and the existing ones did not move.

**A note on the viewpoint.** The first version measured horizon and sky view from the parcel's representative point,
which often falls inside the house (median sky view 34%). It now uses the most open spot on the section (median 67%).
