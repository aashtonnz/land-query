# Sixth fresh-eyes review (T-68, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `128621a..7899e84` (T-65 to T-67) against the published
results (run 42443382855, all blocks compiled at `525ca6e`).

- **Independent boundary.** It used Stats NZ's local-government lines (from GWRC's basemap) as an independent
  boundary.
- **Parcels and tests.** It checked 16 parcels end to end against KCDC and LiDAR, and ran 31 mutants with bytecode
  caching off.
- **Confirmation.** The author re-checked finding 1 before recording it: 3910395 has 1,433 m² inside by KCDC's line
  and 38 m² inside by its ward. The author also confirmed that the published parcels total 1,361 km², of which
  716 km² lies inside the district.

## Findings

| # | Finding | Status |
| --- | --- | --- |
| 1 | 3910395 (Lot 2 DP 10208, Upper Hutt side) is published at 17.4% inside. Only KCDC's line puts land of it in the district; KCDC's ward and Stats NZ give 38 m² (0.46%). Joining the two outlines takes the larger, so slivers where they disagree pass the 1,000 m² floor. | Confirmed, serious |
| 2 | 3836751 (about 2 ha inside by all three outlines) and 3907637 (about 1.5 ha) are dropped, because 1.5–2 ha is under 1% of a large parcel, while smaller pieces are kept. The 1% floor depends on parcel size. | Confirmed, serious |
| 3 | Public mode withholds `district_share_pct` (its source is ◐) yet calls every parcel a district parcel. 20 published parcels have their point outside the district: 700.8 km², of which 63.4 km² is in it. 7694974 is served as a 615 km² parcel with no share, and a bounding-box search over Upper Hutt finds it. | Confirmed, serious |
| 4 | On partial parcels, values use three extents: zones the whole council feature, terrain the fetch window plus 300 m (`open_ground_m2` non-null on 381 parcels without LiDAR), catchments the whole parcel. The docs describe only one. | Confirmed (catchment suspected), minor |
| 5 | 15 of 31 mutants survive, including other floors, a ward buffered by 150 m, the old mirror-gap rule, and the membership code in `fetch_parcels_kcdc.py` itself. | Confirmed, minor |
| 6 | `check_complete.py` passes a block with results but no `provenance.json`. | Confirmed, minor |
| 7 | `SOURCES.md` calls the ward the closer boundary, but the ward alone excludes three parcels that Stats NZ and the line include. | Confirmed, minor |
| 8 | The test fixture's outline differs from the run's by 1.6 ha (simplified). | Confirmed, minor |
| 9 | Q1 orders by `title_types`; safe today, since Q1 is withheld publicly. | Suspected (latent), minor |
| 10 | `kcdc_mirror_vs_linz` counts 27,285, not 27,286, and merged provenance drops the outline's area. | Confirmed, minor |

Checked and correct:
- The outline sha was reproduced from live KCDC services.
- Shares match within 0.1.
- The counts reconcile (27,614 = 27,286 + 317 + 11).
- Title types are unreachable in public mode.
- `lidar_catalogue` works as described.
- The 16 parcels' area, share, zones, LiDAR cells and ground levels match.

## Not checked

- **Needs the LINZ key:** LINZ shapes.
- **Other boundaries:** Horowhenua's and Upper Hutt's own boundaries.
- **Not recomputed:** flow, sun, horizon, roof, earthworks and wind values.
- **Not run:** the workflows.

## What a Kāpiti parcel is (T-69)

Findings 1–4 come from one question: how to publish a parcel that crosses the district boundary. The owner chose
whole parcels (D-18) over publishing only the part inside.

## T-70: fixes (8 Nov 2026)

- **Membership** (1, 2, 7).
  - Land counts as the district where at least two of three boundaries agree: KCDC's line, KCDC's ward and Stats NZ's
    district polygon (GWRC's copy). So no single digitising decides.
  - The sea and islands come from the line's sea loop, without the thin strips where the line alone disagrees on land.
  - A parcel belongs if its point, or at least 1,000 m² of it, lies inside. There is no share floor any more.
  - By KCDC's shapes: 27,284 parcels in 44 blocks. 3910395 (17 m² inside by the majority) is dropped; 3836751 and
    3907637 are kept. Stats NZ's polygon agrees with the ward on 3784322, 4033360 and 3954251, so they are dropped.
- **Public mode** (3). `about` now says that whole parcels are published, that a few reach far outside the district
  (the 615 km² forest section), and what their values cover. The share itself stays withheld until T-35.
- **Extents** (4). `SOURCES.md` now says what each kind of column covers on a parcel crossing the boundary: council
  layers, the fetch window for terrain and buildings, and the mosaic for catchments. `open_ground_m2` comes from
  building outlines, so it is present without LiDAR.
- **Tests** (5).
  - Synthetic and real-boundary tests pin the majority rule, the sea and the islets (Motungarara), the area floor,
    and the publishing check's failed and no-coverage sources.
  - 17 of 17 mutants of the new code are caught, run with bytecode caching off.
  - The fetch script's own lines (which ward type it asks for) still have no test; a wrong query would fail the
    outline build or show in the rebuild's counts.
- **Smaller fixes** (6–10).
  - A block with results but no `provenance.json` stops publishing.
  - The fixture holds all three boundaries, simplified to 0.5 m, and says so.
  - A precomputed query that names a withheld column anywhere in its SQL is withheld.
  - `kcdc_mirror_vs_linz` counts parcels with LINZ geometry (27,285 of 27,286; one has none), as intended.

## T-71: rebuild (8 Nov 2026)

- **Run.** Run 42448558067 compiled all 44 blocks at `3df0677` and published.
- **Checked on the published results:**
  - 27,284 parcels, the number predicted from KCDC's shapes. Counts reconcile: 27,614 = 27,284 + 319 dropped + 11 in
    the two removed blocks.
  - 3910395, 3784322, 4033360 and 3954251 are out.
  - Kept: 3836751 (0.9% inside by LINZ's shape), 3907637 (0.4%), 4024201 (100%), the Motungarara islets and the rock
    off Kapiti Island (3887751).
  - The outline used three sources and was identical in all 44 blocks; one flow grid; no failed source;
    `linz_not_in_mirror` 72. `about` carries the boundary note.
  - 66 parcels cross the boundary. Their whole area is 1,366.5 km², of which 715.6 km² lies inside the district.
  - 450 parcels have no terrain values; `SOURCES.md` now says so.

A seventh fresh-eyes review follows, under fresh-eyes review 1.1.
