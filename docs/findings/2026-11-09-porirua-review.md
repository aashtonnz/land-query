# Twelfth fresh-eyes review: Porirua (T-89, 9 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `ae37a23..1d01a44` (T-86 to T-88: per-council settings and
Porirua) and the first Porirua results (run 42499625052 at `b06e418`). It was told that road and water parcels had
already been found and left out in code.

- **Spot checks.** 14 parcels end to end against PCC's live layers and LiDAR: coast, harbour, hills, the fault, the
  city's edges and Mana Island.
- **Membership.** City membership recomputed from scratch.
- **Kāpiti.** A Kāpiti tile compiled before and after the generalisation, and compared.
- **Tests.** 25 mutants of the per-council code.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | The District Plan 2025 does not apply in the 1999 plan's Plimmerton Farm Zone (PCC's own layer says so), yet its 50 parcels were published with empty zones and `pdp_*` columns, which read as "outside". | Confirmed, serious | T-90 |
| 2 | PCC has not mapped flood hazard in the Horokiri valley (its "Flood Hazard – Unmapped Area", 31.5 km²): 208 parcels there read empty flood columns. | Confirmed, serious | T-90 |
| 3 | Porirua's `about` was Kāpiti's text: attribution to KCDC, Kāpiti's forest section and railway note, KCDC's flood models. | Confirmed, serious | T-90 |
| 4 | Notable tree groups, heritage settings and heritage item extents were not fetched, so `[]` read as "none" on 17 + 8 parcels that have them. | Confirmed, serious | T-90 |
| 5 | PCC's coastal environment layer does not reach Mana Island. | Suspected, serious | T-90 (disclosed) |
| 6 | Notified Plan Changes 1–6 (flood remapping, a heritage deletion) are not in force, are not used, and were not disclosed. | Confirmed, minor | T-90 (disclosed) |
| 7 | District Plan 2025 layers that matter for land decisions were not fetched: precincts, height controls, designations, landscapes, coastal natural character, sites of significance to Māori, the gas pipeline, rail vibration, radio height control, development areas. PCC's draft geohazard layers and flood depths were not used. | Confirmed, minor | T-90 (fetched; drafts disclosed) |
| 8 | The footprints' dates in `SOURCES.md` were unsupported (29,725 of 30,409 are undated); "one survey only" was false (2013–14 LiDAR covers the city). | Confirmed, minor | T-90 |
| 9 | `unmapped_structure_m2` flags far more than `SOURCES.md` implied (above 0 on 44%, 50 m² or more on 12%). | Confirmed, minor | T-90 |
| 10 | The service named the mirror as a source only for "KCDC mirror". | Confirmed, minor | T-90 |
| 11 | The service accepted another council's results. | Confirmed, minor | T-90 |
| 12 | Shared column meanings still carried Kāpiti text for Porirua (winter sun, wind, survey area); Porirua's QA height checks have no matching fields (n = 0). | Confirmed, minor | T-90 in part (QA open) |
| 13 | The outline is in effect PCC's boundary (its boundary and wards differ by 1.2 ha). | Confirmed, minor | Already stated in `SOURCES.md` |
| 14 | The READMEs, `fetch_results.py` and `server.py` did not mention `COUNCIL` or `porirua-results`. | Confirmed, minor | T-90 |
| 15 | 14 of 25 mutants survived. | Confirmed, minor | T-90 |

Checked and correct:
- All 19 polygon layers matched PCC's live layers exactly on 14 parcels, and ground levels matched the LiDAR.
- Every layer is the 2025 plan version, with the right class fields.
- Membership is exact: 0 wrongly in, 0 wrongly out, no parcel in both councils.
- Kāpiti is unchanged.
- The road fix works.
- Public mode leaks nothing about people.

## Not checked

- **Blocked by the proxy:** PCC's ArcGIS Online licence wording.
- **Open questions:** whether the plan puts Mana Island in the coastal environment; the footprints' capture dates.
- **Needs the LINZ key:** LINZ geometry.
- **Not run:** `finish.py` for Porirua.

## T-90: fixes (9 Nov 2026)

- **Where the plan applies** (1, 2, 5, 6).
  - New Porirua columns `plan_1999_plimmerton_farm` (the 1999 plan's zone, where the 2025 plan does not apply) and
    `pcc_flood_unmapped` (where PCC has not mapped flood hazard).
  - P1 now excludes parcels in the unmapped area.
  - `SOURCES.md` and `about` say what an empty value means there, that the coastal environment layer misses Mana
    Island, and that Plan Changes 1–6 and the draft geohazard layers are not used.
- **More layers** (4, 7). 15 more District Plan 2025 layers: notable tree groups, heritage settings and item extents,
  precincts, height controls, designations, four landscape and cultural overlays, five infrastructure and
  development-area overlays. P3 includes the tree groups and heritage settings and extents.
  - A 2 km Plimmerton tile compiles with 93 columns. 15 parcels are marked Plimmerton Farm, 14 of them with empty zones.
    Height controls are on 113 parcels and precincts on 15.
- **Per-council text** (3, 12, 14). Each council's settings carry its own `about` text. Porirua column rows cover
  winter sun, wind and survey area. The server, `fetch_results.py` and the README name the council.
- **Service** (10, 11). The mirror source uses the council's own copy; another council's results are refused.
- **Wording** (8, 9). The footprints are described as mostly undated, the 2013–14 survey is named as not yet used, and
  the warning's district rate is given.
- **Tests** (15).
  - Rules moved into tested functions: the outline from polygons, roads and water left out, the council's columns, the
    renamed building column, building coverage, the queries (now in `inverse_queries_defs.py`).
  - Of 11 mutants of the kind that survived, all 11 are caught.
  - Both councils pass all 23 service tests.
  - The Kāpiti tile still compiles identically, and Kāpiti's queries are unchanged.
- **Still open:** Porirua's QA height checks (no matching fields in PCC's layers), and ground change from the 2013–14
  survey.
