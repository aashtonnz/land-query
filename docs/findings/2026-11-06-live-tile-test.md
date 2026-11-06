# Live tile test: findings (6 Nov 2026)

First contact between the Land Query design and real data. One 1 km × 1 km tile in central Paraparaumu
(NZTM2000 1769000–1770000 E, 5468400–5469400 N), fetched live from public sources. Status: done except
LINZ parcels, titles and easements, which need a LINZ API key (fetcher written, waiting on the key).

## What was fetched

34 sources, 16,002 features, all with URL, fetch time, sha256 and licence note recorded ([`2026-11-06-tile-provenance.json`](2026-11-06-tile-provenance.json)).

| Source | Features in tile | Notes |
| --- | --- | --- |
| KCDC district plan zones | 15 | Zone names in both old and National Planning Standards forms |
| KCDC plan overlays (flood, heritage, notable trees, ecology, noise, coastal) | 14 | Heritage and tree points carry location and legal description |
| KCDC flood hazard classes (stream corridor, overflow path, storage, ponding) | 15 | |
| KCDC recommended building levels (flood levels) | 12,284 points | Both NZVD2016 and Wellington 1953 datums |
| KCDC wastewater manholes / pipes / laterals | 258 / 227 / 502 | Material, diameter, install year, condition grade, criticality |
| KCDC stormwater points / pipes, water supply pipes | 576 / 474 / 740 | |
| KCDC building outlines 2021 | 887 | Include council's own ground and roof heights |
| GWRC liquefaction, earthquake-induced slope failure | 1 / 9 | Liquefaction is one 32 km² polygon from 1:250k geology |
| LINZ 1 m DEM 2024–25, DSM 2024–25, DEM 2021 | 3 × 1,000,000 cells | Kāpiti also has a 2013–14 flight |

Wind/corrosion, tsunami, fault avoidance and earthworks layers returned no features in this tile (correctly: it is inland and off the fault).

## Performance against the T-17 gate

- LiDAR read for the tile: 62 s wall, 142 MB peak (whole COG sheets downloaded and cached; first run).
- Vector fetch: ~2–5 s per layer; RBL points 21 s.
- Compile to DuckDB: 887 units × 47 columns in ~19 s, 252 MB peak.
- Gate was under 5 s and 2 GB. Memory passes easily. Time fails as written, but it is dominated by network
  fetch and one-off tree building; the compute itself is not a constraint. The gate should be rewritten as a
  per-tile cost on the real compute (GitHub Actions), not laptop seconds.

## Data quality findings

1. **Pipe inverts are partial.** Invert levels on 39 of 227 wastewater pipes (17%) but 174 of 258 manholes (67%).
   Gravity analysis is possible but must report "no invert within X m" rather than infer.
2. **The datum problem is solved at source.** KCDC publishes every invert and flood level in both NZVD2016 and
   Wellington 1953. The Gemini design's "auto-correct +0.38 m datum shift" pillar is unnecessary here.
3. **Independent sources agree.** LINZ 2025 DEM vs KCDC building ground heights: median difference −0.11 m
   (5th–95th percentile −0.98 to +0.07 m) across 887 buildings.
4. **LiDAR epochs have a systematic offset.** 2024–25 minus 2021 is +0.08 m on flat ground (IQR 0.06–0.10 m).
   Any change claim must correct for this first.
5. **Real change candidates exist but are unverified.** After the offset, 37 patches of ≥100 m² changed by more
   than 1 m. None lie on 2021 building footprints and none match a KCDC earthworks record. Many show a consistent
   +1.1 to +1.7 m rise, which could be platforms, stockpiles or vegetation classified as ground. Needs an imagery check.
6. **Resolution varies wildly.** GWRC liquefaction is regional geology; KCDC flood levels are point-dense. Every
   value needs a resolution / fit-for-parcel flag, or agents will over-trust coarse layers.

## Competitor comparison (Landsight, verified via its free MCP and a public property page)

- Free MCP: three tools (address search, fetch one property's LINZ record, plans). No area, filter or bulk query.
- Full report (account): zone, hazards, services, schools, feasibility — **but for 10 Tararua Street, Paraparaumu,
  Landsight's own page states stormwater and wastewater layers are held only for Auckland, Christchurch and
  Hamilton, and flood layers only for Auckland and Christchurch, "so nothing is known here either way".**
- KCDC publishes all three openly, with inverts, condition grades and flood levels. In Kāpiti we already hold
  data Landsight does not.
- Premium NZ$49/month, 300 AI requests; free tier 2 reports/day.

## Sourceability audit of the 96-domain schema (by family)

✅ sourced live or clearly open · ⚠ exists but licence, coverage or effort is a real question · ❌ not sourceable,
not legitimately reusable, or excluded by the privacy line

| Family (Gemini domains) | Verdict | Basis |
| --- | --- | --- |
| Cadastre, titles, easements (D01–D03) | ✅ | LINZ CC BY via WFS (needs key). LINZ "Landonline: Title Memorial" table exists, 46M rows, CC BY, updated 31 Oct 2026 |
| Covenant / instrument full text (D02, D54) | ⚠ | Instrument text is a paid LINZ search; memorial index is free |
| Corporate / director graph (D04) | ❌ | Requires owner names (licensed LINZ layer) joined to people; excluded by privacy line |
| LiDAR terrain, slope, change (D05, SIM-01/02) | ✅ | Live, three epochs, CC BY |
| Building outlines and heights (D06) | ✅ | KCDC 2021 with heights; LINZ national outlines |
| Building interiors: bedrooms, cladding, plumbing, Healthy Homes, %NBS (D59–D64) | ❌ mostly | Rating detail and listings not open; EPB register ✅ for commercial only |
| Three waters (D07) | ✅ (KCDC) | Live; other councils vary and must be checked one by one |
| Power, fibre (D08) | ⚠ | Transpower lines open; distribution capacity partial; Chorus port data ❌ |
| Geotech: NZGD, S-map (D09) | ⚠ | NZGD needs registration and has reuse terms; S-map licensed; GWRC liquefaction ✅ but coarse |
| Hazards (D10) | ✅ | KCDC flood classes and levels, coastal erosion scenarios, tsunami; GWRC slope failure. NHC claims per address ❌ |
| Plan zones and overlays (D11 geometry) | ✅ | Live |
| Plan rule text and Planning Act overrides (D11 rules) | ⚠ | Rule text in KCDC ePlan; overrides need careful manual legal encoding |
| Consents and decision documents (D12, D22, D28) | ⚠ | Issued-consent lists exist; officer reports not bulk; Consenty already sells this |
| Heritage, ecology (D13) | ✅ / ⚠ | KCDC overlays, HNZPT list ✅; ArchSite has NZAA terms |
| Traffic, noise (D14) | ✅ | NZTA counts; KCDC noise corridors |
| Valuations, value history (D15, D20) | ⚠ / ❌ | KCDC revaluation service exists (was down); bulk reuse terms unclear; history ❌ |
| Census, schools (D16) | ✅ | Stats NZ, MoE |
| Historic aerials, photogrammetric fill (D18, SIM-10) | ⚠ | Retrolens imagery open; stereo reconstruction is research-grade work |
| Sale history, title transfers with prices (D19) | ❌ | Licensed sales data |
| Groundwater bores, water takes (D21, D32, D37, D66) | ✅ | GWRC services seen (water takes, groundwater) |
| Adjacency graph (D23–D28) | ✅ derived | From parcels once fetched |
| Wind, corrosion, designations (D29, D33) | ✅ | KCDC layers |
| Berm assets, leases, body corporate, insurer status, street point clouds (D30, D31, D34, D35) | ❌ | Not public, ToS-restricted, or not available |
| Plan change submissions (D36) | ⚠ / ❌ | Public but names people; excluded by privacy line |
| LUC, ETS forest, minerals (D40, D67, D68, D65) | ✅ / ⚠ | LRIS LUC and NZP&M permits open; ETS mapping partial |
| Satellite EO (D71) | ✅ | Sentinel-1/2 open, but 10–20 m: area context, not parcel facts |
| Indirect inferences: thermal R-value, SWIR asbestos, letterboxes, ONTs, insurer quote gates, shadow signals (D73–D78) | ❌ | Too coarse to be true at parcel level, ToS breaches, or profiling of occupants |
| Cross-checking (D79–D84) | Method, not data | Keep as QA; several pillars already solved at source |
| Non-private land, Māori land, lineage (D85–D96) | ✅ / ⚠ | DOC and LINZ land open; Pātaka Whenua terms to check; lineage derivable from LINZ |

Rough tally: about a third of the families are cleanly sourceable now, a third need licence or effort decisions,
and a third should be dropped.

## Something to fix regardless

The repo's three "benchmark parcels" use **real addresses with invented facts**. 10 Tararua Street is a real
2,427 m² lot (Lot 2 DP 7318, one 470 m² building per LINZ via Landsight); the fixtures describe a 950 m² section
with an unconsented studio flat and a shell-company director. The repo is private, but the planned GitHub Pages
site and `llms.txt` beacons would publish these claims about real properties and their owners. Fixtures should
use clearly fictional addresses, or real data only.

## What this says about the edge

- Agent-native address lookup is taken (Landsight, free).
- Kāpiti three-waters, flood classes, flood levels and multi-epoch LiDAR change are open, live, and not in
  Landsight's product. Regional depth outside Auckland is a real, current gap.
- Region-wide inverse queries with provenance remain unclaimed by anyone. Not yet demonstrated here, because
  that needs parcels.

## Next

Tracked on [`TASKS.md`](../../TASKS.md):

1. Fetch parcels, recompile on parcels, and run region-wide inverse queries with provenance (T-16, T-33).
2. Replace the invented benchmark fixtures (T-30).
3. Licence and resolution register for every source (T-31).
4. Check the change candidates against aerial imagery (T-29).
5. Reset proposal: pruned schema and revised board, for approval (T-32).

## Licence notes (checked 6 Nov 2026; not legal advice)

- LINZ parcels, titles without owners, easements, building outlines, LiDAR, title memorial index: free, CC BY 4.0.
- LINZ owner names: free but restricted to the LINZ Licence for Personal Data; excluded by the privacy rule.
- LINZ instrument copies (covenant text): $8 each through Landonline.
- KCDC layers: some marked CC BY 4.0, some with no licence stated; each needs checking.
- S-map: free for non-commercial use only; commercial licence required, price not published.
- GNS active faults database: commercial use not permitted. Use council fault overlays.
- NZGD: registration and terms of use; resale unlikely to be permitted.
- Sales, valuation history, listings: paid commercial sources; out of scope for now.
