# Plan

Full descriptions for open tasks in `Next` and `Planned` on [`TASKS.md`](TASKS.md). Scope: decision D-12
([`DECISIONS.md`](DECISIONS.md), [reset proposal](docs/proposals/2026-11-06-reset.md)).

## Next (Phase 1 — Kāpiti Coast)

- **T-44: QA and query wording**
  Split QA check 1 by network and asset type, and settle the Te Horo block from its asset types and both datum levels.
  Run the area check in every block, against LINZ. Q4 uses each block's epoch offset and is renamed or given a building
  condition; Q5 uses containment and returns feature ids. Paging reads `properties.exceededTransferLimit` and compares
  totals with `returnCountOnly`. A parcel without an id fails the run.
- **T-45: Raw-source sample check**
  Through GitHub Actions, fetch the raw features for 10 or more named parcels (urban, rural, coastal, block edge) and
  compare their compiled values; then rebuild the district once with T-40 to T-44 and record the before and after counts.
- **T-36: Query service**
  A read-only MCP server over the compiled Kāpiti database: area or filter queries return parcel rows, each value with its
  source, fetch time, licence, value kind and fit-for-parcel flag. Run locally or from GitHub first; serve outside users
  only licence-cleared data, after T-35.
- **T-29: Check LiDAR change candidates**
  For a sample of the 256 Q4 parcels not on recent survey plans (district run), compare LINZ 7.5 cm aerials from before and after and classify each
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
