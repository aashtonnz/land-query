# Plan

Full descriptions for open tasks in `Next` and `Planned` on [`TASKS.md`](TASKS.md). Scope: decision D-12
([`DECISIONS.md`](DECISIONS.md), [reset proposal](docs/proposals/2026-11-06-reset.md)).

## Next (Phase 1 — Kāpiti Coast)

- **T-56: Ground change on clear ground**
  Compute `dz_2021_2025_*` on cells where the 2025 DSM is within 0.5 m of the DEM, add the parcel's vegetated share
  (DSM − DEM over 0.5 m, outside 2021 building outlines), and re-run the T-29 sample: the 8 vegetation hits should
  drop out of Q4 and the 13 real changes stay. Takes effect at the next rebuild.
- **T-25: Source-change checks**
  A weekly workflow that fetches each source layer's field list and record count (and the LINZ layer revision where available),
  commits a snapshot, and flags any difference.
- **T-24: Second council**
  Write the adapter for one more council (Porirua or Wellington City): map its layers to the same columns, check its
  height datum, licence and inverts, and record the effort, to price the rest of the region.

## Planned (Phase 2 — Greater Wellington)

- **T-38: Rest of Greater Wellington**
  Wellington City, Hutt City, Upper Hutt and Porirua, using what T-24 learned.
