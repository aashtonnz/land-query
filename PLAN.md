# Plan

Full descriptions for open tasks in `Next` and `Planned` on [`TASKS.md`](TASKS.md). Scope: decision D-12
([`DECISIONS.md`](DECISIONS.md), [reset proposal](docs/proposals/2026-11-06-reset.md)).

## Next (Phase 1 — Kāpiti Coast)

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
