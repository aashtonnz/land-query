# Seventh fresh-eyes review (T-72, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `7899e84..e0989f5` (T-69 to T-71) against the published
results (run 42448558067, all blocks compiled at `3df0677`).

- **Membership.** It rebuilt the district outline from live sources and applied it to all 27,614 mirror parcels. That
  reproduced the published set exactly (27,284 parcels, no differences), and it found no in-district parcel missing
  and no out-of-district parcel included.
- **Other checks.** It checked the 66 crossing parcels' shares against GWRC's copy of LINZ parcels, checked 13
  parcels' ground levels against the 2024–25 DEM, and ran 37 mutants with bytecode caching off.
- **Confirmation.** The author re-checked finding 1 before recording it: the building outline layer's extent stops
  at 1762723 E and 5458562 N, and returns no features on Kapiti Island.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | Where KCDC's 2021 building outlines don't reach (Kapiti Island and its islets, the far south and north, and land outside the district), parcels read 0 m² of buildings, and the whole parcel as open ground. KCDC's valuations show improvements on Motungarara A2 ($126,000), A1A, A1B and Section 3 Block I Kapiti SD ($846,000). On crossing parcels, buildings outside the district are never counted. An empty value reads as 0 (D-12). | Confirmed, serious | T-73 |
| 2 | In blocks without LiDAR, `open_ground_m2` is empty while `building_2021_m2` is 0; elsewhere the same situation gives the whole parcel as open ground. | Confirmed, minor | T-73 |
| 3 | The ward and Stats NZ follow the same meshblocks (median 0.08 m apart), so "two of three" is in practice Stats NZ's boundary; the docstring overstated it. | Confirmed, minor | T-73 |
| 4 | `about` says "centre point"; the code uses the representative point (they differ on 5 crossing parcels). | Confirmed, minor | T-73 |
| 5 | `about` says terrain covers the fetched part (`coverage_pct`); it covers the part with LiDAR (`lidar_coverage_pct`). | Confirmed, minor | T-73 |
| 6 | `about` doesn't say that about 70 railway parcels are missing. | Confirmed, minor | T-73 |
| 7 | `survey_area_m2` repeats Kapiti Island's 17.6 km² on each of its 36 parts. | Confirmed, minor | Documented (T-73) |
| 8 | Mutants surviving: floor value and `>=`, centroid for the representative point, share rounding, the open-ended SQL pattern, the mirror gap's district test, and `fetch_parcels_kcdc.py` itself. | Confirmed, minor | T-73, except the fetch script |
| 9 | A licence-withheld column used only in a precomputed query's WHERE passes if its source is missing from the query's source list. No current query does this. | Suspected (latent), minor | Open |

Checked and correct:
- Membership reproduces the published set exactly.
- Crossing parcels' shares agree across all three boundaries and with GWRC's parcels.
- The sea loop adds only islets, Motungarara and one esplanade reserve.
- Ground levels match the 2024–25 DEM on 13 parcels, and zones match KCDC's on 6.
- Public mode leaks nothing about people.

## Not checked

- **Needs the LINZ key:** LINZ geometry, titles and the 72 missing parcels.
- **Blocked by the proxy:** Horowhenua's GIS.
- **Not attempted:** flow, sun, wind and three-waters values.

## T-73: fixes (8 Nov 2026)

- **Buildings** (1, 2).
  - Each block records where every council layer was captured (its extent), and the district outline is saved.
  - A new column, `buildings_coverage_pct`, gives the share of each parcel inside the building outlines' coverage
    (the layer's extent within the district).
  - Below 99%, the building area and every column measured on open ground or roofs are empty, not 0: 14 columns,
    from `open_ground_m2` to the platform earthworks.
  - In blocks without LiDAR, open ground is now the window area less buildings, as elsewhere.
  - Checked on two local tiles. The Motungarara islets, Tahoramaurea and Tokomapuna come out empty (they read 0
    before). All 361 parcels in central Paekākāriki keep their values.
- **Wording** (3–7).
  - The outline's docstring says the ward and Stats NZ are effectively one boundary.
  - `about` now says "representative point", names `lidar_coverage_pct` and `buildings_coverage_pct`, and says that
    about 70 railway parcels are missing.
  - `SOURCES.md` warns against summing `survey_area_m2`.
- **Tests** (8).
  - New tests cover the building rule, the floor at exactly 1,000 m², a frame-shaped parcel whose centroid lies in
    the district, one-decimal shares, a name that only starts like a withheld column, and the mirror gap's district
    test.
  - All 13 mutants of this kind are caught, run with bytecode caching off.
  - `fetch_parcels_kcdc.py`'s own lines remain untested; the rebuild's counts check them.
