# Eleventh fresh-eyes review (T-84, 9 Nov 2026)

A new reviewer, briefed with the repository only, reviewed `704fa1e..3588181` (T-81, T-82) against the published
results: full run 42459146212, finished by `finish.yml` run 42477497763.

- **Before and after finishing.** It compared the published results before and after finishing, column by column.
- **Local tiles.** It compiled local tiles with the old code plus `finish.py` and with the current code, and compared
  them.
- **Recall.** It measured the LiDAR warning's recall more realistically: 10% of outlines hidden, the rest kept.
- **Sweep and tests.** It swept the table for empty values, 0s and falses, and ran 34 mutants with bytecode caching
  off.

**No serious finding.** Under fresh-eyes review 1.1, the run of reviews that began with the fourth (T-61) ends here.

## Findings

| # | Finding | Status | Fix |
| --- | --- | --- | --- |
| 1 | 3818065 shows 99.0% coverage with empty building values: run 42459146212 used the unrounded rule, and finishing can only empty, never restore. Not disclosed in RUN.txt, `about` or `SOURCES.md`. | Confirmed, minor | T-84 (disclosed; restored at T-83) |
| 2 | RUN.txt doesn't say that `unmapped_structure_m2` is missing, though the building columns' description points to it. | Confirmed, minor | T-84 |
| 3 | The publishing check doesn't test the T-81 flow rule; `finish.yml` runs fewer checks than `kapiti.yml`. | Confirmed, minor | T-84 |
| 4 | No test runs `finish.py`; the pending-column exemption has no limit, so a full rebuild that lost the column would pass. | Confirmed, minor | T-84 |
| 5 | 11 of 34 mutants survive in the structure test's growing step, the compiler's own LiDAR conditions (re-applied by `finish_row`, so the output is unchanged), the column list and `about`. | Confirmed, minor | T-84 in part |
| 6 | `SOURCES.md` overstates the warning for small buildings: the 63% is for 60–80 m² only; for 40–60 m² it finds about 22%. | Confirmed, minor | T-84 |

Checked and correct:
- Finishing changed only the values the rules empty, with exactly the counts in `finish.json`. Columns, types, rows,
  provenance, QA and queries are otherwise identical.
- Old code plus finishing equals the current code on two local tiles, apart from the pending column.
- The rules can't invent or double-apply.
- The warning's rates hold: 90% of hidden buildings of 60 m² or more, 163 of 2,557 parcels flagged.
- The remaining 0s and falses are documented.
- Public mode leaks nothing about people.

## Not checked

- **Needs the LINZ key:** LINZ geometry and titles.
- **Not done:** photo checks of the new flags, and a run of `finish.yml` itself.
- **Seen, not investigated:** 25 freehold parcels with `title_count` 0; parcel 7760250 with `area_m2` 0 and
  `open_ground_m2` 1.

## T-84: fixes (9 Nov 2026)

- **Disclosure** (1, 2).
  - `finish.py` writes `finish_note.txt`, which says it is not a rebuild, which pending columns are missing, and how
    many parcels a rebuild would restore building values to (here 1).
  - `finish.yml` puts the note in RUN.txt, which `about` passes on.
  - `finish.json` records both figures.
- **Checks** (3, 4).
  - The publishing check now also refuses flow or warning values on parcels under 99% LiDAR.
  - A new `test_finish.py`, run by `finish.yml` before publishing, checks `finish.py`: rules applied, rows and
    columns kept, whole numbers kept whole, idempotent, and its limits reported.
  - Pending columns may be missing only from results that RUN.txt says were finished (`catalogue.missing_columns`,
    tested).
- **Tests** (5). New cases cover the 2 m gap round outlines, the regrow step and a tall stack at a roof's edge.
  - Of the 7 mutants re-run, 6 are caught.
  - Growing into cells over 15 m survives: such a cell next to a planar roof core barely occurs.
  - The compiler's own LiDAR conditions duplicate `finish_row`'s, which every row passes through.
- **Wording** (6). `SOURCES.md` gives the rates by size, including about 22% for 40–60 m².
