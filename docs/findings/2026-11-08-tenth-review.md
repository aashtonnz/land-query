# Tenth fresh-eyes review (T-80, 8 Nov 2026)

The GitHub budget was used up, so T-79 was not rebuilt for the district. A new reviewer, briefed with the repository
only, reviewed `f3b08c2..704fa1e` (T-79) on local tiles instead.

- **Tiles.** It compiled 5 new tiles (Ōtaki, Te Horo, Paekākāriki, Paraparaumu south and a LiDAR-edge tile) plus the
  author's t79 tile, with the old and new code on the same data.
- **Photo checks.** It judged about 75 parcels on LINZ's 2025 0.075 m photos, which match the 2024–25 LiDAR in time.
- **Detector recall.** It measured how often the detector finds real buildings by hiding 3,552 outlines.
- **Tests.** It ran 25 mutants with bytecode caching off.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | T-79's smoothness test rejects roofs steeper than about 23°: with outlines hidden it found 62% of buildings, 18% at 23–26° and 4% at 30° or more. 22 houses confirmed on the 2025 photos still read 0 m² of buildings. | Confirmed, serious | T-81 (D-19) |
| 2 | Small buildings are missed even with flat roofs (only the interior was counted): 15% of 60–80 m² buildings found. | Confirmed, serious | T-81 |
| 3 | `unmapped_structure_m2 = 0` reads as "no unmapped building" where the detector missed one, or where only part of the parcel has LiDAR. | Confirmed, serious | T-81 |
| 4 | T-79 emptied `upslope_area_truncated` under partial LiDAR but left `flow_path_m` and `upslope_area_max_m2`, which are served publicly: 3801495 at 0.1% LiDAR reads a flow path of 0 and 2 m² upslope. | Confirmed, serious | T-81 |
| 5 | False alarms are commoner than stated: of about 50 flags checked, about 26 are real structures and 21 trees. Correct values on parcels with outlined houses were emptied (3757086, 3765783, 4003381, …). | Confirmed, minor | T-81 (D-19) |
| 6 | Wording overclaims and is out of date (the detector "finds" houses; the capture-area row; `about`; the truncation description; "empty never stands for 0" against the RBL count; a misnamed parcel in the ninth-review record). | Confirmed, minor | T-81 |
| 7 | 10 of 25 mutants survive, including the height floor, largest vs total patch, and serving the column publicly. | Confirmed, minor | T-81 |

Checked and correct:
- On 4 tiles, only the intended columns changed between old and new code.
- The author's flagged houses are caught.
- Water tanks, vehicles and steep ground caused no flags.
- Public mode withholds every building column and the new one.

## Not checked

- **Needs the LINZ key:** LINZ geometry, titles and easements.
- **Not sampled:** a random sample of unflagged parcels; glasshouses.
- **No photos:** Kapiti Island and the foothills.
- **Not attempted:** a district-wide count of missed houses.

## T-81: fixes (8–9 Nov 2026)

- **What a building value is** (1, 2, 5; D-19).
  - A simple LiDAR test can't separate roofs from trees well enough. The author swept the settings on t79:
    - the 3×3 smoothness test (T-79) finds 62% of hidden-outline buildings and flags 70 parcels;
    - a 3×3 plane fit finds 90% and flags 163, mostly round tree crowns;
    - 5×5 plane fits find 7–66% and flag 12–82.
  - The owner chose to keep KCDC's outlines as the basis and to say so plainly. `building_2021_m2` is the area under
    KCDC's 2021 outlines, and open ground is the land outside them; 0 m² means no outline, not no building.
  - `unmapped_structure_m2` is now a separate warning that never empties a value. It uses the plane fit, which
    catches 90% of buildings (98% of roofs at 23–26°), and counts the whole footprint.
- **Empty where unknown** (3, 4).
  - `unmapped_structure_m2` is empty where LiDAR covers under 99% of the parcel.
  - So are `upslope_area_max_m2`, `upslope_area_truncated` and `flow_path_m`.
- **Wording** (6).
  - `SOURCES.md`, `about` and the capture-area row say what the building columns are and what the warning catches,
    with its measured rates.
  - The RBL exception is stated.
  - The ninth-review record names 3817530 correctly (Lot 16 DP 46556).
- **Tests** (7).
  - New tests cover pitched roofs at 10°, 25° and 35°, a 2 m flat object, two separate patches, a denser crown, the
    warning never emptying values, and the column's sources (withheld publicly).
  - All 8 mutants of this round are caught.
- **Waiting for a rebuild.** The rebuild waits on the budget (T-80); it will also publish T-79's other fixes.
