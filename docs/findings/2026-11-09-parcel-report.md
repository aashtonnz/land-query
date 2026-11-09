# Parcel report on demand (T-101)

9 November 2026. Tier 2 of the national MVP (D-21): the full 1 m analysis for one parcel anywhere in New Zealand.

## What was built

- `pipeline/councils/national.py`: a third setting for the existing pipeline, with no council layers. Parcels, titles
  and building outlines come from LINZ's public ArcGIS services (D-22), or from the LINZ Data Service with the key
  (which adds easements). Ground and surface heights come from LINZ's national 1 m LiDAR mosaics
  (`new-zealand/dem_1m`, `dsm_1m`). The pipeline reads only a window around the parcel from each 24 × 36 km sheet,
  never the whole file.
- `pipeline/parcel_report.py OUT --id ID | --address "ADDRESS"`: finds the parcel, sets a block just big enough to hold
  it (parcels up to 3 km across), runs the pipeline, and writes `report.json`. The file holds the parcel's values, the
  LiDAR surveys under it with their dates, producers and licensors (from the mosaics' capture-dates files), the parcel
  and nearby building shapes, and the provenance.
- `pipeline/report_page.py`: the report as one page. Each value comes with what it means, and values not known show
  as "not known", never 0.
- `.github/workflows/report.yml`: the same on GitHub with the key (about US$0.02 a report). Not yet run.

Changes to shared code:
- Without a district (`OUTLINE kind "none"`), the block alone decides which parcels belong.
- Parcels repeated in a service are kept once (as in T-100).
- Without the key, titles come from LINZ's public service.
- Easement and covenant counts are now empty, not 0, when the non-primary parcels were not fetched. This was a
  latent fault for any council block whose LINZ fetch failed.

## Results

| Parcel | Time | LiDAR survey found |
| --- | --- | --- |
| Lot 1 DP 78602, 9 Milne Drive, Paraparaumu | 44 s | Kāpiti Coast 2024–25, 100% |
| 12 Hereford Street, Christchurch Central | 53 s | Christchurch 2024–25, 100% |
| 15 Queen Street, Northcote Point, Auckland | 55–63 s | Auckland Part 1 2024, 100% |

All three ran in this session at no cost. About half of each run is the 10 m catchment grid (27 s); the 1 m LiDAR
window takes about 10 s.

**Check against Kāpiti.** For 9 Milne Drive the report and the published Kāpiti results agree on area, ground heights,
slope, horizon, sky view, wind inputs, winter sun (3.3 h both) and the 1 m flow. The differences come from the inputs:
- building area: 1,401 m² from LINZ's outlines against 1,416 m² from KCDC's;
- the 10 m catchment: 36,700 m² against 41,700 m², because its grid covers 8 km around the parcel rather than the
  district.

Sample page: https://claude.ai/artifact/PxLFZ1SQFgHk5uqDXiNeYV (private).

## Limits

- Parcels over 3 km across are refused, for memory.
- Easements need the key, so a GitHub run (`report.yml`).
- No council data: zoning, overlays, flood maps and three waters are listed on the page as not included.
- LINZ's building outlines miss buildings newer than their photos; `unmapped_structure_m2` warns of most.
- Serving reports to customers on request needs a small server, which the owner decides on (D-21, Part 4).
