# Ninth fresh-eyes review (T-78, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `1bd1829..f3b08c2` (T-76, T-77) against the published
results (run 42459146212, all blocks compiled at `0b921c2`). It also swept the whole table for empty values, 0s and
falses that read as facts.

- **Methods.** It drew KCDC's live outlines over LINZ's 2017 and 2021 aerial photos, and built a simple building
  detector from the 2021 DSM.
- **Spot checks.** 11 parcels against live sources.
- **Tests.** 19 mutants, run with bytecode caching off.
- **Confirmation.** The author re-checked finding 1 before recording it. On the 2017 photo, Lot 87 DP 325584
  (6703303) has a house with no outline, while every neighbour has one. It is published with 100% coverage and
  0 m² of buildings.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | KCDC's outlines miss some houses inside the area they cover: about 8 established houses found among 77 flagged parcels (6703303, 3776223, 6694710, 4036629, 3775496, …), plus about 6 being built in January 2021. They are published as 0 m² of buildings, with the whole parcel as open ground. The search only looked at parcels with a street number and no outline, so there are probably more. | Confirmed, serious | T-79 |
| 2 | The building rule ignores the fetch window: 7203031 shows 58 m² of its 1,059 m² of outlines (`coverage_pct` 95.1). | Confirmed, serious | T-79 |
| 3 | `about.empty_values` says empty means "outside that mapped hazard, within the area the council modelled". That is false for 266 parcels (238 km²) outside every KCDC flood layer, Kapiti Island included. | Confirmed, serious | T-79 |
| 4 | `ww_pipe_condition_grade` is 0 ("not graded") on 163 parcels, below the 1–5 scale, so a filter for good pipes picks it up. | Confirmed, serious (documented) | T-79 |
| 5 | `gw_liquefaction`: empty is called "not mapped", but GWRC maps only soils with significant potential. | Confirmed, minor | T-79 |
| 6 | The capture-area row says outlines exist wherever it reaches, and is marked fit ✅; most outlines were drawn from 0.3 m photos; the licence tally is out of date (23 rows, now 28). | Confirmed, minor | T-79 |
| 7 | 6 of 19 mutants survive, including the compiler's withholding call and the district clip (no test runs `compile_tile.py`). | Confirmed, minor | T-79 in part |
| 8 | `easements_n` and `land_covenants_n` read 0 where no easement parcel is surveyed, which is not "no easements". | Confirmed, minor | T-79 (documented) |
| 9 | `upslope_area_truncated` is false on 22 parcels under 99% LiDAR coverage. | Suspected, minor | T-79 |
| 10 | 3818065 still shows 99.0% with empty values (fixed in code at T-77, not yet published). | Confirmed, minor | Next rebuild |

Checked and correct:
- Capture area: none of the outlines lies wholly outside it.
- Building areas: they match the outlines' union.
- The district clip on coverage is right.
- 11 parcels' area, zones, flood, tsunami, DEM and nearest manhole match the live sources.
- `rbl_in_parcel_n` is never 0.
- Public mode leaks nothing about people.

## Not checked

- **Needs the LINZ key:** LINZ geometry, titles and easements.
- **Outline gaps:** their full count.
- **Not attempted:** sun, roof, horizon and wind values; water-main distances; rural water schemes; the weekly
  check of the capture area.

## T-79: fixes (8 Nov 2026)

- **Unmapped buildings** (1).
  - A new modelled column, `unmapped_structure_m2`, gives the largest building-like structure on the parcel that no
    2021 outline covers, from the 2024–25 LiDAR. That means 2.5–15 m above the ground, with a smooth surface, at
    least 3 m wide and more than 2 m from any outline. It is measured on the structure's interior.
  - From 40 m², the building and open-ground columns are empty.
  - It catches houses KCDC missed and houses built since 2021.
  - Tried on a 2.5 km tile (2,557 parcels at Paraparaumu and Raumati), it flagged 70. That includes 6703303 (142 m²)
    and 3776223 (98 m²), and 39 parcels that had read 0 m².
  - On the aerial photos, Lot 16 DP 46556 (3817530; first misnamed Lot 4 DP 58017, which is 3837395) is a whole house without an outline. Two of three flags checked on
    parcels that do have outlines were dense trees, and one was a reserve's trees.
  - False alarms only empty a parcel's building values; they never invent one. `SOURCES.md` says so.
- **Fetch window** (2). Building values are also empty when the fetch window covers less than 99% of the parcel.
- **Empty values** (3–5, 8, 9).
  - `about` and `SOURCES.md` now give the flood models' rough extent, and say that outside it empty means not
    modelled.
  - Liquefaction: empty means outside GWRC's significant-potential areas.
  - Condition grade 0 is published empty.
  - The easement counts' 0 is explained.
  - `upslope_area_truncated` is empty, not false, on parcels under 99% LiDAR.
- **Wording** (6). The capture-area row says what it is (⚠). The tally is now 28 rows, 15 ✅ and 13 ◐, and T-35's
  count is updated.
- **Checks** (7).
  - The publishing check also requires building values to be empty under 99% window coverage or with an unmapped
    structure, and refuses a condition grade of 0.
  - New tests cover the LiDAR structure test (a flat roof found; tree crowns, a hedge, a mast and a lean-to touching
    an outline not), the 40 m² threshold, the window rule, multi-feature capture areas and the share on a
    triangular parcel.
  - All 11 mutants of this round are caught, run with bytecode caching off.
  - The compiler's own wiring is covered only by the publishing check.
