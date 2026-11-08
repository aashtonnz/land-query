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

## Pending: what a Kāpiti parcel is

Findings 1–4 come from one open question: how to publish a parcel that crosses the district boundary. Three
reviews have now found problems at that edge. The fix waits on the owner's choice (T-69).
