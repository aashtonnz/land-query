# Plan

Full descriptions for open tasks in `Next` and `Planned` on [`TASKS.md`](TASKS.md). Scope: decision D-12
([`DECISIONS.md`](DECISIONS.md), [reset proposal](docs/proposals/2026-11-06-reset.md)).

## Next (Phase 1 — Kāpiti Coast)

- **T-47: Flow at the coast**
  In `flow.py`, a valid cell next to no data drains into it when that is its steepest drop. Mask the flattened sea in the
  national DEM (for example where the 8 m contour DEM has no data, or at the survey's constant sea value) in
  `district_flow.py`, the 1 m block flow and the wind height mean. Use 10 m cells whose centre is in the parcel.
  Checks: a slope to a sea column drains each row to its own beach cell; the Waitohu cell at 1780895, 5493975 reads
  80 km² or less; parcel 3883291 reads under 1 km².
- **T-48: Provenance and publishing safety**
  `merge_sources` takes URL and licence from the first block that has them; test with a no-coverage block first.
  `kapiti.yml` refuses to push when `only` is set or blocks are missing, and writes the commit SHA to `RUN.txt`.
- **T-49: Ties, overlaps and caveats**
  Nearest manhole and pipe: report all assets tied within 5 cm (Q1 uses the deepest invert, Q3 the worst grade, both
  stated). Flag parcels where zones of different types overlap. Count a parcel as clipped only if it lies at the
  district boundary. Note the 1979 and 1980 install-year spikes in Q3. The smaller points in finding 9.
- **T-50: Rebuild and re-check**
  Rebuild the district with T-47 to T-49, re-run `sample_check.py` and the reviewer's checks, and record before and
  after.
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
