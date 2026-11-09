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
