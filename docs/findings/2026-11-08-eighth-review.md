# Eighth fresh-eyes review (T-75, 8 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `e0989f5..1bd1829` (T-73, T-74) against the published
results (run 42454216635, all blocks compiled at `4a8e65c`). It was also asked to look, in every source, for an
empty value that reads as "none" where a layer was never captured.

- **Buildings.** It downloaded all 50,623 building outlines and compared them with LINZ's aerial-photo capture areas.
- **Aerials.** It checked houses on the 2021 aerials.
- **Parcels and tests.** It checked 11 parcels against live sources and ran 26 mutants with bytecode caching off.
- **Confirmation.** The author re-checked finding 1 before recording it. All but 2 of the outlines lie inside the
  2017 urban photos' 232 km² footprint. Waiorua Kapiti 6 Block (3830470), Lot 1 DP 51707 at Reikorangi (3972863) and
  Lot 2 DP 85433 (3795250) are published with `buildings_coverage_pct` 100 and 0 m² of buildings.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | T-73 took the building layer's bounding box as where outlines were captured. They were captured only inside the 2017 urban photos' footprint, an irregular shape. 586 published parcels count as covered but lie outside it; 562 read 0 m² of buildings, with the whole parcel as open ground (209 km²). Houses are visible on the 2021 aerials at Waiorua Bay on Kapiti Island, at Reikorangi and on the east edge. Q4 returns 10 of them. | Confirmed, serious | T-76 |
| 2 | `gw_eq_slope_failure` is empty on 991 parcels where GWRC never mapped it (Kapiti Island, the eastern hills), 270 of them steeper than 25°. Elsewhere the layer classes all land, so empty reads as "not susceptible". | Confirmed, serious | T-76 (documented: empty means not mapped) |
| 3 | Public mode serves 6 flood layers and withholds 4. 9,614 parcels inside a withheld one show every served flood column empty, with no sign that data was held back. | Confirmed, minor | T-76 (`about` says so) |
| 4 | `rbl_in_parcel_n` reads 0, never empty, including on 541 parcels outside KCDC's flood models. | Confirmed, minor | T-76 |
| 5 | The viewpoint columns (horizon, sky view, wind) are kept on parcels without building coverage, although `SOURCES.md` says every open-ground column is withheld. The values are probably sound: the viewpoint must also be clear in the 2024–25 DSM. | Confirmed, minor | T-76 (wording) |
| 6 | 17 of 26 mutants survive. Among them: deleting the compiler's withholding call, dropping three columns from the list, using the outline's envelope, and serving `buildings_coverage_pct` publicly. No check before publishing asserts the rule. | Confirmed, minor | T-76 |
| 7 | 12 parcels lie at least half inside GWRC's Kāpiti rivers 1% AEP extent with every KCDC flood column empty. Most are slivers; for two, KCDC's own layers have nothing nearby. | Suspected, minor | Open (KCDC data) |
| 8 | `SOURCES.md` says `gw_liquefaction` is "one 32 km² polygon"; 21,847 parcels carry a class. | Confirmed, minor | T-76 |

Checked and correct:
- The flow model uses the DEM only.
- 10 parcels' ground levels match the DEM to 0.01 m; areas, building areas (where outlines exist) and zones match
  KCDC.
- The 234 parcels withheld by T-73 are empty in every building column.
- River corridors agree with GWRC's.
- Tsunami zones cover Kapiti Island.
- Public mode leaks nothing about people.

## Not checked

- **Needs the LINZ key:** LINZ geometry, titles and easements.
- **Not attempted:** sun, roof, wind and horizon values; three-waters completeness; whether the outlines are complete
  inside the footprint.

## T-76: fixes (8 Nov 2026)

- **Building coverage** (1, 5, 6).
  - Coverage is now LINZ's capture area for the 2017 0.1 m urban photos (a new ✅ source,
    `buildings_capture_area`, fetched with each block), within the district.
  - Checked on two local tiles. At Reikorangi, 53 of 53 parcels are now empty, including 3972863, 3862718 and
    3810410. In central Paekākāriki, all 361 parcels keep their values.
  - The service tests, which run before every publish, now fail if any parcel under 99% coverage has a building
    value.
  - New tests use the real footprint (Waiorua Bay, Reikorangi and the east edge lie inside the bounding box but
    outside the footprint), the exact column list and the column's sources. All 7 mutants of this kind are caught.
  - `SOURCES.md` explains why the viewpoint columns stay.
- **Empty values** (2–4, 8).
  - `rbl_in_parcel_n` is empty where there are no points (the publishing check fails on a 0).
  - `SOURCES.md` says what an empty overlay means: outside a mapped hazard within the modelled area, or, for layers
    that class all land (`zones`, `gw_eq_slope_failure`), not mapped.
  - `about` gains an `empty_values` note, including that some flood layers are withheld publicly.
  - The liquefaction row is corrected.
- **Not yet in the weekly source check:** the capture area.
