# LiDAR ground-change candidates against aerial photos (T-29, 8 Nov 2026)

Q4 ("Ground level changed since 2021") returns 558 parcels in run 42374135961. 300 of them are on survey plans from
DP 550000 onward, which are mostly new subdivisions. This check looks at the other 258, which T-21 left unexplained.

## Method

- **Sample.** 24 of the 258, chosen at random (seed 29, reproducible).
- **Photos.** Each parcel was shown side by side in LINZ's 7.5 cm Kāpiti Coast aerial photography from 2021 and 2025
  (CC BY 4.0: LINZ, AAM NZ, Aerial Surveys, KCDC), which matches the two LiDAR surveys. The images were read at 0.3 m,
  with the parcel outlined, by `pipeline/aerial_pairs.py`, which rebuilds them.
- **Classes.** Each change was put in one of these classes, by eye:
  - earthworks;
  - construction (a new or rebuilt house, with its site works);
  - vegetation (scrub, forest or long grass counted as ground by the LiDAR classification);
  - a natural change (beach, river);
  - an artefact (no visible change).
- **Cost.** Nothing on GitHub; the photos are read directly from LINZ's public bucket.

## Results

| Class | Parcels | Share of the 23 classified |
| --- | --- | --- |
| Construction | 6 | 26% |
| Earthworks | 5 | 22% |
| Natural (beach, river) | 2 | 9% |
| Vegetation | 8 | 35% |
| Artefact | 2 | 9% |
| No 7.5 cm imagery in either year | 1 | — |

- **Real ground change.** About two thirds of the candidates (13 of 23) show real change to the ground: earthworks,
  construction, or a beach or river bed.
  - Several "not recent" parcels are new houses on lots from plans just below DP 550000 (DP 523514, 538654, 549577).
    The DP-number test undercounts recent subdivision.
  - Two are expressway works (Peka Peka to Ōtaki).
- **Spurious hits.** About a third (8 of 23) are vegetation: dense scrub, forestry slash growing back, or long grass,
  where the LiDAR ground surface differs between surveys. Two more show no visible change; both are around existing
  houses, where ground under roofs and paving is interpolated.
- **What it means for Q4.** Read Q4 as "worth a look", not "earthworks happened". Its question already says the
  results are unverified. A follow-up (T-56) would measure ground change only on clear ground (nothing standing above
  it in the 2025 DSM) and report the vegetated share of each parcel. Both checks below are what should drop.

## The sample

| Parcel | Appellation | Mean change after offset (m) | Largest cell change (m) | Class | What the photos show |
| --- | --- | --- | --- | --- | --- |
| 3869949 | Lot 4 DP 75319 | +0.63 | 3.7 | earthworks | site cleared of trees and filled; now a yard with sheds |
| 7260293 | Lot 12 DP 413488 | -0.35 | 3.0 | earthworks | graded section on a new road; neighbouring houses built |
| 7859475 | Section 36 SO 505426 | +0.37 | 3.0 | vegetation | dense scrub and wetland, unchanged in the photos |
| 7812036 | Lot 2 DP 505104 | +0.79 | 5.4 | construction | bush cleared and a new house built |
| 8083018 | Lot 50 DP 538654 | +0.40 | 2.2 | construction | new house on a bare section |
| 7510101 | Lot 75 DP 762 | +0.31 | 1.3 | vegetation | long grass and scrub around an existing house |
| 3984383 | Lot 58 DP 87805 | -0.46 | 2.8 | artefact | existing houses and driveway, no visible change |
| 6833882 | Lot 2 DP 349465 | +0.44 | 1.8 | vegetation | 64 m² strip through bush |
| 7918678 | Lot 4 DP 523514 | -0.43 | 2.1 | construction | new house on a grassed section |
| 3929761 | Lot 13 DP 35028 | -1.30 | 4.7 | natural: beach | foreshore; the beach surface dropped |
| 7626752 | Section 1 SO 489585 | +1.04 | 4.7 | earthworks | Peka Peka to Ōtaki expressway embankment |
| 3831664 | Lot 1 DP 24431 | -0.72 | 1.3 | vegetation | 99 m² roadside strip of scrub |
| 7031480 | Lot 4 DP 390657 | +0.33 | 1.3 | construction | new house; bush cleared |
| 6991875 | Lot 1 DP 366314 | +0.42 | 2.5 | vegetation | scrub regrowth on a hillside |
| 3918575 | Lot 2 DP 81570 | +0.35 | 6.1 | no imagery | no 7.5 cm aerial tile in either year (Te Horo foothills) |
| 8120344 | Lot 3 DP 549577 | +0.52 | 2.0 | construction | new house in a new street |
| 3994406 | Lot 9 Block III DP 2465 | +0.33 | 2.6 | vegetation | house under dense trees, unchanged |
| 3998193 | Part Wairarapa Block | +0.46 | 1.1 | natural: river | gravel river bed reshaped |
| 4035772 | Lot 1 DP 75822 | +0.82 | 6.2 | earthworks | expressway interchange earthworks, now planted |
| 3959367 | Haruatai B Block | +0.40 | 2.6 | earthworks | new graded track; scrub regrowth |
| 6526579 | Lot 27 DP 91189 | +0.47 | 2.5 | vegetation | long strip of scrub and young trees |
| 3938633 | Lot 5 DP 29663 | -0.31 | 2.7 | artefact | existing house, minor yard change |
| 3794457 | Topaatekaahu 5 Block | +0.36 | 2.1 | vegetation | forestry slash in 2021, young trees in 2025 |
| 4006358 | Lot 1 DP 7224 | -0.39 | 2.0 | construction | old house demolished and a new one built |
## T-56: the clear-ground rule, tested before changing anything (8 Nov 2026)

The proposed rule: measure ground change only on clear ground (2025 DSM within 0.5 m of the DEM, at least 50
cells), and apply Q4's thresholds to that. It was tested on the same 23 parcels, reading the 2021 and 2024–25 LiDAR
directly from LINZ (`scratchpad` script; the old rule reproduced Q4 for all 23).

| Photo class | Flagged by Q4 now | Flagged under the clear-ground rule |
| --- | --- | --- |
| Real change (construction, earthworks, beach, river) | 13 | 10 |
| Vegetation | 8 | 4 |
| No visible change | 2 | 0 |

- **More precise, but it loses real changes.** The share of real changes among flagged parcels rises from 57% to 71%,
  but 3 real new-house sites drop out: excluding the new house as "not clear ground" leaves too little of the site to
  pass the thresholds.
- **Decision.** Q4 is unchanged. The compiler adds `dz_2021_2025_clear_pct` and `dz_2021_2025_clear_mean_m` beside
  the existing columns, so a user can compare the two. They take effect at the next rebuild; on the test tile the
  two means correlate at 0.97, and 44% of cells are clear on average.
