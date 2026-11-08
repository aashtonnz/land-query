# Fifth fresh-eyes review (T-64, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed everything changed since the fourth review
(`aa1d01a..128621a`: T-62 and T-63) against the published results (run 42441707069, blocks from run 42437281659 at
`cebe28e`).

- **Independent boundaries.** It checked district membership against two independent outlines: KCDC's 2025 ward
  polygons (the Māori ward covers the whole district, 731.5 km²) and GWRC's local-government polygons (731.2 km²).
- **Parcels and tests.** It checked 13 parcels against live KCDC zones, GWRC parcels and the 2024–25 DEM, and ran
  18 mutants.
- **Confirmation.** The author re-checked finding 1 before recording it, using KCDC's own parcel shapes: 17
  dropped parcels have district land (7.6 km²). The reviewer's 63 km² used GWRC's shapes for two very large lots,
  which the mirror holds cut short.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | T-62's rule (keep a parcel only if its representative point lies in the district) drops parcels partly inside the district, 7.6 km² of district land by KCDC's shapes. One parcel wholly inside is dropped: Part Blk III Akatarawa SD, 4024201, which KCDC's boundary line cuts although its ward polygon and GWRC's both hold the whole parcel. Two more are mostly inside: 7344506 (67%) and 3868849 (53%). District-wide queries miss them. | Confirmed, serious (author's grading; the reviewer graded it minor, as an omission) | T-65 |
| 2 | KCDC's boundary line and its own ward polygons disagree in 11 slivers over 2,000 m² (largest 6.1 ha, near Paekākāriki). | Confirmed, minor | T-65 |
| 3 | `district_share_pct` is measured against the line alone (up to 5 points off the ward-based share), and `SOURCES.md` wrongly says council overlays cover only the part inside: zoning often covers the whole parcel. | Confirmed, minor | T-65 |
| 4 | Public mode withholds `district_share_pct` (its KCDC source is ◐), so public users can't tell which 45 parcels cross the boundary. | Confirmed, minor | Waits on T-35 (KCDC licence) |
| 5 | 15 of 18 mutants of the T-62 code survive both test suites, including no district filter, the old mirror-gap rule, any LiDAR error counted as no coverage, no retry or status check, and the automatic `sea_mask` removed. | Confirmed, minor | T-65 |
| 6 | `SOURCES.md` says 543 parcels have no terrain; the published results have 438. | Confirmed, minor | T-65 |
| 7 | The boundary used for membership isn't in provenance (fetched separately from `district_boundary`). | Confirmed, minor | T-65 |
| 8 | The flow-grid check ignores blocks with no district-flow record. | Confirmed (code), minor | T-65 |
| 9 | The "Life Estate" title type is served publicly on 4 parcels; it signals a living person's life interest. No names, title references or owners are served. | Suspected, minor | Owner's decision |

Checked and correct:
- Every published parcel is in or touching the district.
- The counts reconcile with the mirror (27,614 = 27,265 + 337 + 12).
- The LiDAR no-coverage flags agree with the live catalogue.
- All blocks share one flow grid.
- 13 parcels' areas, shares, ground levels and zones match the live sources.

## About people

Finding 9 is for the owner. Everything else served publicly is about land.

## Not checked

- **Needs the LINZ key:** LINZ shapes, titles, easements and the 72-parcel gap.
- **No independent source reached:** Stats NZ's boundary (blocked) and Horowhenua's.
- **Not run:** the LiDAR retry under real failures.
- **Not recomputed:** flow, sun, horizon, roof, earthworks and wind values.

## T-65: fixes (8 Nov 2026)

- **Membership** (1–3).
  - The district outline is now KCDC's boundary line closed at sea, joined with its whole-district ward polygon
    (`district_outline`, a new source with its own provenance).
  - A parcel belongs if its representative point lies inside, or if at least 1% and 1,000 m² of it does. The
    floor keeps out slivers where the two outlines differ.
  - `district_share_pct` is measured against the joined outline.
  - By KCDC's shapes the district has 27,288 parcels (21 added back, including 4024201, 7344506 and 3868849). Block
    1795000_5470000 returns, for one large parcel (7694974) whose point lies there.
  - `SOURCES.md` no longer says council layers stop at the boundary.
- **Tests** (5).
  - Membership, the mirror gap, the parcels error and the LiDAR catalogue are now functions with tests.
  - `check_complete.py` reads blocks through a tested function.
  - A real-outline fixture checks Kapiti Island, the cut parcel and three neighbouring districts.
  - Of 20 mutants (the reviewer's, adapted, and new ones for the rule), all 20 are caught. The compiler's and
    merge's own script code (the reviewer's M13, M14, M16) is still untested; the rebuild's checks cover those
    columns.
- **Smaller fixes** (6–8).
  - `SOURCES.md` says 438.
  - The outline's sources and sha are in each block's provenance.
  - A block without a district-flow record stops publishing.

## T-66: rebuild (8 Nov 2026)

- **Run.** Run 42443382855 compiled all 44 blocks at `525ca6e` and published. An earlier attempt was cancelled within a
  minute: a test had failed on my machine only, from stale bytecode left by the mutation run (see T-65).
- **Checked on the published results:**
  - 27,286 parcels (27,288 by KCDC's shapes; LINZ's shapes differ slightly), all with `district_share_pct`, which is
    as low as 1.0%; 51 parcels are below 100%.
  - All the parcels the review named are back, including 4024201 (100% inside), 7344506, 3868849, and the two large
    lots the reviewer measured with GWRC's shapes: 7267649 (28.8%) and 7694974 (6.5% of 615 km², about 40 km²).
  - Counts reconcile with the mirror: 27,614 = 27,286 + 317 dropped by the blocks + 11 in the two blocks still
    removed (Horowhenua and Upper Hutt).
  - `linz_not_in_mirror` is 72. All 44 blocks used one district-flow grid and one district outline, and none had a
    failed source.
  - 449 parcels have no terrain values; `SOURCES.md` now says so.

A sixth fresh-eyes review follows, under fresh-eyes review 1.1.
