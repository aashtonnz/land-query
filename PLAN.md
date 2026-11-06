# Plan

Full descriptions for open tasks in `Next` and `Planned` on [`TASKS.md`](TASKS.md). Scope: decision D-12
([`DECISIONS.md`](DECISIONS.md), [reset proposal](docs/proposals/2026-11-06-reset.md)).

## Next (Phase 1 — Kāpiti Coast)

- **T-21: Full Kāpiti compile**
  List the 1 km NZTM2000 tiles that overlap the Kāpiti Coast district boundary, run [`tile.yml`](.github/workflows/tile.yml)
  for each (a matrix job or a loop of dispatches, within the free Actions minutes), and merge the per-tile results into
  one database keyed by LINZ parcel id, keeping each parcel once (taking the tile it lies mostly within). QA checks on every tile,
  written to the results: council manhole lid levels against LiDAR ground; KCDC building ground heights against LiDAR;
  the 2021 to 2024–25 LiDAR offset on flat ground; parcel area against LINZ `calc_area`. Also count instruments per parcel
  for R-5.
- **T-37: Cheap computed measures**
  From the 1 m DEM and DSM already fetched: sun hours on the open ground of each parcel at the winter solstice and
  annually, and the share in shade; horizon angle and view openness; overland flow paths and upslope catchment
  (D-infinity) across the parcel; roof planes (pitch, aspect, area) and solar potential from the DSM within building
  outlines; cut and fill to make a level platform of a given size; an approximate AS/NZS 1170.2 terrain and shielding
  category. Each gets one independent check (for example overland flow against KCDC overflow paths, roof area against
  building outlines). In `SOURCES.md`, each compiled column is marked published, derived or modelled, with its method.
- **T-39: Fresh-eyes review**
  Start a new session with only the repository: the code, `SOURCES.md`, D-12 and the latest results, not earlier
  summaries. Review the fetchers, compiler, QA checks and queries for wrong joins, unit or datum mistakes, edge effects
  and misleading column meanings, and check a sample of result rows against the raw sources. Each fix comes with a check
  that fails on the old code and passes on the new. Do this before T-36 is offered outside.
- **T-36: Query service**
  A read-only MCP server over the compiled Kāpiti database: area or filter queries return parcel rows, each value with its
  source, fetch time, licence, value kind and fit-for-parcel flag. Run locally or from GitHub first; serve outside users
  only licence-cleared data, after T-35.
- **T-29: Check LiDAR change candidates**
  For the five Q4 parcels not on recent survey plans, compare LINZ 7.5 cm aerials from before and after and classify each
  change as earthworks, construction, vegetation or artefact.
- **T-25: Source-change checks**
  A weekly workflow that fetches each source layer's field list and record count (and the LINZ layer revision where available),
  commits a snapshot, and flags any difference.
- **T-24: Second council**
  Write the adapter for one more council (Porirua or Wellington City): map its layers to the same columns, check its
  height datum, licence and inverts, and record the effort, to price the rest of the region.

## Planned (Phase 2 — Greater Wellington)

- **T-38: Rest of Greater Wellington**
  Wellington City, Hutt City, Upper Hutt and Porirua, using what T-24 learned.
