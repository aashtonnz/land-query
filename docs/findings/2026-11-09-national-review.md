# Sixteenth fresh-eyes review: national index, parcel report and map site (T-103, 9 Nov 2026)

Three new reviewers, each briefed with the work and its sources only, reviewed:
- the national index (`pipeline/national_index.py`, the Greater Wellington pilot);
- the parcel report (`pipeline/parcel_report.py`, `report_page.py`, `councils/national.py`) and the shared pipeline
  code it changed;
- the public map site (`site/build_map.py`, `site/map.js`, `site/map.html`, `pages.yml`).

They recomputed values from LINZ's live services and the LiDAR source files, and could change nothing. Each finding
below was checked before it was fixed.

## Findings

Seriousness: serious = an error that would otherwise have gone unnoticed and misled a user.

| # | Part | Finding | Seriousness | Status |
| --- | --- | --- | --- | --- |
| 1 | Report | In a gap in the national LiDAR mosaic, the no-data value was read as a height: ground −9,999 m, LiDAR cover 100%, and invented sun, sky view and roof values (confirmed on sheet BK35 and parcel 3977522). A boundless windowed read does not mask the file's own no-data value | Serious | Fixed (T-107), with a test that fails without the fix. Heights at or below −100 m are dropped in council builds too |
| 2 | Report | Where the mosaic has ground LiDAR but no surface model (Kaikōura 2016–17, Tasman 2008–15), every surface-based value was invented | Serious | Fixed (T-107): surface-model columns (`overlays.DSM_COLUMNS`) are empty unless the surface model covers 99% of the parcel's ground; checked on parcel 8767165 |
| 3 | Index | Partly cancelled titles (status PRTC, 27,567 nationally) were treated as missing: 3,457 pilot parcels showed no title type, and `titles_not_found` was 86% wrong | Serious | Fixed (T-108); also in the report's no-key title fetch |
| 4 | Index | Shore and island parcels fell outside the region's simplified district polygons: about 83 missing, including Kapiti Island's shore sections and reclaimed Seaview lots | Serious | Fixed (T-108): the region is grown by up to 1 km within 300 m of the coast only |
| 5 | Index | `statutory_actions` names who land vests in (companies, trustees), against "facts about land, never people" (D-12) | Moderate | Fixed (T-108): dropped |
| 6 | Index | Road frontage included up to 1 m of each side boundary at both ends (1.4–1.8 m too long) | Moderate | Fixed (T-108): 0.1 m tolerance; test tightened |
| 7 | Index | 40–60 seabed and riverbed parcels with the old "DCDB" intent remained | Minor | Fixed (T-108): Riverbed and Streambed intents, and bed names (not "Old … Bed") excluded |
| 8 | Index | `ground_cells_pct` under 100 mostly reflected sampling on small parcels, not missing data | Moderate (misleading) | Fixed (T-108): now the share of the parcel's own cells that have ground |
| 9 | Map | 76 council parcels with no national-index shape were drawn as squares of their area over other parcels, up to 9.6 km²; at least one was superseded | Moderate | Fixed (T-109): shape from LINZ by id; parcels LINZ no longer has are left off the map |
| 10 | Map | Topo50 1:50k lakes covered parts of house sections (311 parcels over 10%) | Moderate | Fixed (T-109): lakes are clipped to land outside parcels |
| 11 | Map | In dark mode, "no value" grey matched land without parcels | Moderate | Fixed (T-109): its own colour; the legend explains water and land without a parcel |
| 12 | Map | "Sewer installed 1,980" (thousands separator); KCDC's 1979–80 years are likely placeholders for about half of Kāpiti's pipes | Moderate | Fixed (T-109): years unformatted, with the caveat in the panel and legend |
| 13 | Map | Labels overstated: point-sampled ground, catchments that may be larger, "1,000" for "≤1,000" | Minor | Fixed (T-109) |
| 14 | Map | Page text: "Every parcel in New Zealand" on a Greater Wellington map; "all 27,227" matched when 7 and 1 did not; a link to a private sample report; the map opened on a private home | Minor | Fixed (T-109) |
| 15 | Map | Text from the data went into the page as HTML (not exploitable with LINZ data today) | Minor | Fixed (T-109): escaped |
| 16 | Map | Workflow: publishing rights granted to the build job; the site did not rebuild when results changed | Minor | Fixed (T-109): rights on the deploy job only; weekly rebuild |
| 17 | Map | Search could bury an exact match | Minor | Fixed (T-109): exact matches first |
| 18 | All | The results branches still hold `titles` and `title_types` (D-15, D-17) | Serious before any announcement | Open: T-106 |
| 19 | Report | Ground and surface models from different surveys (Waiau: 2016–17 ground, 2013 surface) with no warning | Moderate | Open: T-110 |
| 20 | Report | A 47 m building with no LINZ outline reads as open ground under trees | Moderate | Open: T-110 |
| 21 | Report | The 10 m catchment differed widely from the Kāpiti build on a coastal parcel; which is right not settled | Suspected | Open: T-110 |
| 22 | Report | `report.json` holds title references (D-15); several page explanations leave out their limits (500 m horizon, 300 m shadows); an address over several parcels takes the first | Minor | Open: T-110 |
| 23 | Index | Overlapping duplicate parcels (84 pairs) lose elevation cells; slope at 10 m is about 2° gentler than at 1 m; Chatham Islands and a national region source need handling for T-102 | Minor | Open: T-102 (documented) |

## The Kāpiti building-area difference

The index's LINZ outlines are 20 m² or more smaller than KCDC's on 22% of Kāpiti parcels. The reviewer found three
causes:
1. KCDC's "2021" layer is mostly from 2017 0.3 m photos (45,448 of 50,623 outlines); LINZ's here come from 2021
   7.5 cm photos.
2. LINZ captures nothing under 10 m², while KCDC includes 7,658 small outlines (sheds).
3. KCDC's outlines are drawn wider.

In the 2024–25 surface model, 76–80% of the KCDC-only area stands more than 2 m above the ground, so much of it is
real roof or structure. Neither is exact. `SOURCES.md` now says LINZ's outlines are buildings of 10 m² or more.

## Checked and found correct (summarised from the three reports)

- **Index:** recomputed from live data on 50 parcels; area, building area and count, addresses, titles and coast
  distance matched (coast on 3,000 parcels within 0.3 m); ground height within ±0.4 m of the 1 m DEM; no duplicate ids;
  tile edges handled; no owner fields.
- **Report:** windowed LiDAR reads match the source sheets cell for cell, across a sheet boundary; survey names and
  shares match the cells; values match the Kāpiti build on town, hill and survey-edge parcels; cross-lease and unit
  title types match LINZ; the shared-code changes leave the council builds' outputs unchanged (identical KCDC features,
  no repeated ids, old paths unchanged).
- **Map:** no withheld column or owner data in any published file; every council value matches its source for all
  49,238 council parcels, and every national value for all 168,164 others; every parcel appears once per level;
  shapes within 0.53 m; the colour scales are correct; 32 of 33 test clicks hit the right parcel (the miss was 2.1 m²).

## Next

Findings 1–4 were serious, so after the fixes a new reviewer reviews again (fresh-eyes review 1.1). Finding 18
(T-106) must be done before the project is announced anywhere.

## Seventeenth review: the fixes (T-111)

A new reviewer reviewed the T-107 to T-109 fixes. Three of them had serious faults of their own:

| # | Finding | Seriousness | Fix |
| --- | --- | --- | --- |
| 1 | The bed-name rule dropped titled and reclaimed land (railway land "Part Bed Poirua Harbour", 3.8 ha at 476 Hutt Road): 36 pilot parcels, 926 nationally, 94 with titles | Serious | A bed by name only when its intent is DCDB, it has no title and it has no address (476 Hutt Road is untitled but addressed) |
| 2 | The 0.1 m frontage tolerance missed roads set 0.2–0.3 m off the lot line: 291 parcels went from over 5 m to 0 | Serious | 1 m to the road, less only the short end pieces (1.5 m or less) shared with a neighbouring parcel. A first attempt that subtracted all boundary shared with other parcels zeroed 532 frontages, because thin reserve strips run between many lots and their roads; caught in the check of the rebuilt pilot before publishing |
| 3 | Clipping lakes by parcels erased Lake Wairarapa, whose bed is a 75 km² parcel | Serious (map) | Lakes are clipped only by parcels mostly outside them |
| 4 | The coastal margin took 11 Waikawa Beach (Horowhenua) parcels into Greater Wellington | Moderate | A parcel in the margin whose address names another district is left out |
| 5 | Sun and horizon treat missing surface-model cells nearby as open sky | Suspected | Open: T-110 |
| 6 | Seven of the fixes had no test that failed when the fix was undone | Moderate | New tests; each of ten fixes now fails a test when undone (the compiler's call to the surface-model rule is the exception, as the compiler is a script) |
| 7 | −100 m dropped a real height (Martha pit, −101 m); two ground-change columns use the surface model; stale page text; railways called land without a parcel | Minor | Floor −1,000 m; columns added; text corrected |

Checked correct by this reviewer: the council builds are not changed by T-107 (no surface-model gaps or heights near
−100 m in their surveys, and their read path already masked no-data); the Kaikōura and gap parcels now read unknown;
partly cancelled titles are counted once; the shore parcels are present; the map's escaping, search order and workflow
rights.

As this review had serious findings, a further fresh review followed the fixes (T-112).

## Eighteenth review: the second round of fixes (T-112)

| # | Finding | Seriousness | Fix (T-113) |
| --- | --- | --- | --- |
| 1 | Cutting lakes by every parcel mostly outside them erased small lakes lying inside farm parcels: 309 lakes over 0.5 ha lost over 80% (Lake Pounui, Boggy Pond) | Serious (map) | Lakes are cut only within 25 m of their edge (about Topo50's accuracy); their middles are never cut |
| 2 | Lake-bed parcels (Lake Wairarapa 75 km², Ōnoke) are index rows described as flat, low-lying land | Serious | A measured `water_pct`: share under Topo50 lakes and LINZ river areas, plus the sea share of its 10 m cells. Rows are kept, and the map draws parcels mostly under water as water |
| 3 | The bed rule still dropped 16 reclaimed harbour parcels that the DEM shows are land, and kept a parcel 98% harbour because it has an address: paperwork, not land | Serious | The name-based bed rule is removed: no row is dropped by its name, title or address; water is measured (2) |
| 4 | Tests that read source text, or did not run the changed code: inverting the region rule or the bed rule failed no test | Moderate | Tests now run `index_tile` itself on made-up LINZ data (no network); undoing each of 11 rules fails a test |
| 5 | A margin parcel with no address kept (Lot 2 DP 72858, Horowhenua) | Moderate | Its district from the nearest address within 1 km |
| 6 | Frontage counted across thin reserve strips, where legal access may be barred (1.6% of lots, more than 5 m) | Moderate | Reported apart: `road_frontage_via_strip_m` |
| 7 | River beds named as beds showed as land on the map | Minor | LINZ river areas drawn as water; with (3) such parcels are rows whose water share is measured |
| 8 | The 10 m grid still dropped heights below −100 m | Minor | Same −1,000 m floor |

Checked correct by this reviewer: frontage on 2,001 lots measured independently (no wrong zeros; corner, rear and
offset-road lots match); partly cancelled titles; the LiDAR read path and the surface-model rule.

The serious findings were all in water and parcel membership, decided until now from names and paperwork. T-113
replaces that with measurement, and a fourth fresh review follows (T-114).


## Nineteenth review: measured water (T-114)

| # | Finding | Seriousness | Fix (T-115) |
| --- | --- | --- | --- |
| 1 | Kapiti Island, Mana Island and Motungarara parcels (41) were dropped: no address within 1 km, so no district | Serious | A margin parcel is left out only on positive evidence (an address, or the nearest within 1 km, in another district); otherwise it stays |
| 2 | Lake Ōnoke counted twice: its surface is below 0.5 m with no 8 m DEM, so the grid's "sea" overlapped the lake (Lot 43 DP 12843: 45% water read 85.8) | Serious | Water by area of the union of sea, lakes and rivers; the grid is not used |
| 3 | Missing elevation data read as 100% sea (would hit the Chatham Islands) | Serious (national) | As 2: sea is outside LINZ's land outline, never from the grid; a window with no land outline stops the run |
| 4 | Tidal flats read as land (22 parcels mostly seaward of the coast read under 20%) | Moderate | As 2: the Topo50 land outline puts tidal flats in the sea |
| 5 | The map's 25 m edge cut erased most lakes inside farm parcels (4,237 of 4,912) and stretches of the Hutt, Ruamāhanga and other rivers | Serious (map) | Only thin slivers (nothing left after shrinking by 25 m) are cut; the build now reports the share of lake and river area drawn |
| 6 | Parcels 50% or more water were drawn wholly as water | Moderate | Removed: water is drawn from the water layers over the parcels |
| 7 | Six ways to break the water and margin rules passed the tests | Moderate | New tests through `index_tile`: water counted once, no grid used, lake over sea, islands kept; each rule fails a test when undone |
| 8 | SOURCES said Lake Wairarapa's bed reads 100 (95.8); the river-areas layer is a 2018 snapshot | Minor | Corrected and recorded |

Each round has found fewer and narrower faults, but four rounds running have found serious ones, all in rules I wrote
to guess something the data does not say directly. T-115 replaces the last of them with plain area measurement.
