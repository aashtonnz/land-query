# What a second council cost (T-24, 9 Nov 2026)

T-24 was to add one more council, to measure the cost before the rest of the region (T-38). Porirua City is now
compiled by the same pipeline (`porirua-results`: 21,954 parcels, 94 columns), and four fresh-eyes reviews have
checked it, the last with no serious finding.

## Work

- **Generalising the pipeline (T-86, T-87).** Kāpiti's constants moved to `pipeline/councils/kapiti.py`; the compiler,
  QA, queries, measure check, catalogue, service and workflows read the council's settings. Kāpiti's test tile
  compiles identically, and its service output is byte-identical.
- **Porirua's settings.** `pipeline/councils/porirua.py`, 169 lines: 39 layers, class fields, columns left out or
  renamed, outline sources, LiDAR, the service's `about` text. Its `SOURCES.md` section has about 30 register rows and
  15 column rows.
- **Size.** From `ae37a23` to now: 24 files, about 1,100 lines added and 210 removed, in about a day of agent work.
- **Reviews.** Four fresh-eyes reviews (twelfth to fifteenth), each followed by fixes. Their serious findings were
  Porirua-specific, and only a review could have caught them:
  - where the 2025 plan does not apply (Plimmerton Farm);
  - where flooding is not mapped (Horokiri) or the mapping's basis is unknown;
  - Kāpiti text in Porirua's description;
  - missing plan layers;
  - shapes inflated by a repair that never mattered for Kāpiti.

## GitHub cost

- **Rebuilds.** Five full Porirua rebuilds at about US$1 each (17 blocks).
- **Republishing.** Each costs about US$0.02 through `finish.yml`.
- **Reviews and tile checks.** These ran on the session's machine at no GitHub cost.

## What the next council would take

- **Settings.** The settings file and `SOURCES.md` rows: half a day to a day, most of it reading the council's layers
  and plan status (operative version, areas where it does not apply, unmapped hazards).
- **Rebuilds.** Two to four full rebuilds at about US$1–2 each, depending on size.
- **Reviews.** Two to four review rounds. The lessons now in the code should shorten these:
  - shape repair;
  - columns left out or renamed;
  - per-council text;
  - query tests on a table.
- **Three waters.** Still excluded for the Wellington councils (D-16); Wellington Water's licence bars commercial use.

## Still open

- **T-95.** Porirua's QA has no height check of its own.
- **Data improvements.**
  - LINZ's national building outlines would replace PCC's undated footprints.
  - Ground change from the 2013–14 LiDAR.
  - Notified Plan Changes 1–6 when in force.
- **T-83.** Kāpiti's next rebuild (the LiDAR warning column).
