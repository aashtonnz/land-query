# Inverse queries on live parcels: findings (6 Nov 2026)

Follows the [live tile test](2026-11-06-live-tile-test.md). Same Paraparaumu tile (NZTM2000 1769000–1770000 E,
5468400–5469400 N), now compiled on real parcels and queried in reverse: "which parcels match these conditions?"
rather than "tell me about this address". Full results with SQL and provenance:
[`2026-11-06-inverse-queries.json`](2026-11-06-inverse-queries.json). Scripts: [`pipeline`](../../pipeline/).

## Parcels without a LINZ key

The LINZ key still is not visible to sessions, so parcels came from KCDC's public `Cadastral` map service
(`maps.kapiticoast.govt.nz/.../Public/Cadastral/MapServer/0`). It is a mirror of LINZ NZ Primary Parcels: same fields
(LINZ parcel `id`, appellation, titles, survey and calculated area), so ids join to LINZ directly (D-11).

- 582 primary parcels in the tile, fetched in about 2 s; 490 lie wholly inside it.
- **Checked against LINZ.** Lot 2 DP 7318 (10 Tararua Street) is 2,427 m² here, as in LINZ's record seen through
  Landsight. Compiled polygon areas match LINZ `calc_area` to within 0.5 m² for every parcel.
- **Compared with LINZ directly (T-34, once the key was available).** LINZ WFS returned 637 parcels for the tile.
  51 of the extras are not in the tile at all (the WFS filter matches bounding boxes, not shapes); the other 4 are railway
  parcels, which the mirror leaves out. The 582 shared parcels have identical appellation, titles and intent, and their
  shapes differ by at most 0.06 m². Both have the same newest plan (DP 627447), so the mirror shows no lag.
- **Titles and easements from LINZ.** 667 titles (528 freehold, 106 cross lease, 16 unit title, 14 leasehold), with
  type and estate only; owner names are not fetched (privacy rule). 328 non-primary parcels: 322 easements,
  6 land covenants. Every title reference on the parcels resolves. Of the 490 parcels wholly inside the tile, 32 are cross lease only,
  105 have at least one easement.

Compile on parcels: 582 units × 59 columns in 15 s.

## Five inverse queries

All five run over the 472 parcels wholly inside the tile (20 m² or larger), together in under 0.2 s. Each row returns the
parcel id and appellation, the values it was selected on, and the URL, sha256, fetch time and licence of every
source used.

| Query | Conditions | Parcels |
| --- | --- | --- |
| Q1 Gravity-serviceable infill candidates | High or General Residential (≥90%), ≥800 m², <25% built (2021), p90 slope <10°, no flood overlay, manhole with invert ≤30 m and ≥1 m below lowest ground; title type and easements returned | 16 (all freehold) |
| Q2 Recommended floor level well above ground | Built on, and highest KCDC recommended building level inside the parcel >1 m above mean ground | 8 |
| Q3 Nearest sewer old and in poor condition | Nearest wastewater pipe ≤20 m, installed before 1980, condition grade 4–5 | 18 |
| Q4 Ground change since 2021 | Some cell changed >1 m, and parcel mean changed >0.3 m after the 0.08 m epoch offset | 30 |
| Q5 Heritage, notable tree or ecological site | Heritage or tree point on the parcel, or ecological site overlap | 17 |

Spot checks: pipe KWWP002225 (Q3) is earthenware, 1976, grade 5 in the raw KCDC data; manhole KWWN004240 (Q1) has
invert 11.1 m NZVD2016 in both raw and compiled data.

## What the results say

1. **Inverse queries work, and they're cheap.** On one tile, five multi-source questions take a fraction of a second once compiled.
   The cost is all in fetching and compiling, which is already measured (T-17).
2. **Two independent sources corroborate the LiDAR change signal.** 25 of the 30 Q4 parcels are on plans numbered
   DP 550000 or above (recent subdivisions), against 18% of parcels overall. Most of the ground change is
   new subdivision earthworks, which the cadastre confirms independently. That makes T-29's imagery check
   smaller: the five remaining older-plan parcels are the ones to look at.
3. **A first query can be wrong in a convincing way.** The first version of Q2 compared lowest ground with the highest
   recommended building level within 10 m and matched 206 parcels (44%). A recommended building level is a minimum *floor* level
   including freeboard, and the 10 m window picked up upslope values. Restated (levels inside the parcel, against
   mean ground, described as a floor-height requirement) it matches 8, all fully within KCDC's ponding overlay.
   Each column needs a plain definition next to the value, not just a source (feeds R-10, T-31).
4. **Shared-DP reuse is far lower than the design assumes.** The 457 residential parcels sit on 124 plans
   (about 3.7 lots per plan); 38% are on a plan with 10 or more lots in the tile, and 93% share a plan with at
   least one other lot. These are lower bounds, because plans cut by the tile edge are undercounted. D-2 assumes up to
   1:64. Sharing one uploaded document per plan still helps, but nowhere near enough to make the
   covenant-text problem go away (R-5; for T-32).
5. **Condition grade 0 is common** (60 of 582 nearest pipes) and is treated as "not assessed". This needs confirming against
   KCDC's data dictionary (T-31).

## Against Landsight and Relab

- **Landsight**: its free MCP looks up one address or property at a time and has no area or filter query. For Kāpiti
  it holds no stormwater, wastewater or flood data (previous findings). It cannot answer Q1–Q4 here.
- **Relab**: Premium search filters by zoning, services ("connections"), size and subdivision suitability, but
  Relab says its development data (consents, zoning, services, flooding) is only available in
  Auckland, Waikato, Canterbury and Queenstown Lakes ([Relab for lenders](https://relab.co.nz/business-type/financial-advisor)).
  Its filters are fixed fields in a web app; there is no agent-facing query, and API access is Enterprise only
  ([Relab help](https://help.relab.co.nz/en/article/welcome-to-relab)).
- So for Kāpiti, queries Q1–Q4 are not answerable in either product today. This is the edge the earlier findings
  described: regional depth outside Auckland, queried by area, with provenance on every row.

## Not yet done

- More than one tile; plan siblings across tile edges (T-21).
- Plain-language column definitions and fit-for-parcel flags (T-31).
