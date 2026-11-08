# `land-query`

An area-queryable parcel fact service for AI agents, starting with Kāpiti Coast, New Zealand. Agents ask questions such as
"which residential parcels over 800 m² are flat, outside flood overlays and can drain to a sewer by gravity?", and get back
parcel rows in which every value carries its source, fetch time, licence and a fit-for-parcel flag (decision D-12 in
[`DECISIONS.md`](DECISIONS.md)).

This project follows [ai-working-practices](https://github.com/aashtonnz/ai-working-practices):
- Agent instructions: [`AGENTS.md`](AGENTS.md)
- Task board: [`TASKS.md`](TASKS.md)
- Decision log: [`DECISIONS.md`](DECISIONS.md)
- Risk list: [`RISKS.md`](RISKS.md)
- Plan details: [`PLAN.md`](PLAN.md)
- Sources, licences and column definitions: [`SOURCES.md`](SOURCES.md)
- Style note: [`STYLE.md`](STYLE.md)

## What exists now

- **[`pipeline/`](pipeline/)**: scripts that fetch one 1 km × 1 km NZTM2000 tile live from public sources (LINZ parcels,
  titles, easements and LiDAR; KCDC zoning, overlays, flood hazards and levels, three-waters assets and buildings; GWRC
  hazards), compile one row of facts per parcel into DuckDB, and run inverse queries with provenance on every row.
- **[`.github/workflows/tile.yml`](.github/workflows/tile.yml)**: runs the pipeline for any tile on GitHub Actions, using
  the `LINZ_API_KEY` repository secret. One tile takes about 2.5 minutes; results go to the `tile-results` branch.
- **[`.github/workflows/kapiti.yml`](.github/workflows/kapiti.yml)**: compiles the whole Kāpiti Coast district (27,284
  parcels, about 105 columns including computed sun, roof, flow and earthworks measures, 44 blocks) in about 40
  minutes (about US$2.20), with quality checks on every block. It pushes the merged parcel table, provenance and query
  results to the `kapiti-results` branch. Ten fresh-eyes reviews have checked it (`docs/findings/`).
- **[`.github/workflows/porirua.yml`](.github/workflows/porirua.yml)**: the same for Porirua City (T-24): the pipeline is
  per council (`pipeline/councils/`, chosen by `COUNCIL`), and Porirua's results go to the `porirua-results` branch. Its
  sources are LINZ, Porirua City Council (District Plan 2025) and GWRC, without three waters (D-16); see
  `SOURCES.md` ("Register: Porirua City").
- **[`site/`](site/)**: the project page, a parcel explorer of both councils showing only public-mode columns (T-98). `python3 site/build_site.py OUT.html` builds it from the published results; it is published as a private Claude page.
- **[`.github/workflows/finish.yml`](.github/workflows/finish.yml)**: applies the row rules (`finish_row` in
  `pipeline/overlays.py`) to the published results and republishes them, in a few minutes for about US$0.02, with the
  same service checks. Use it for fixes that only change how a parcel's own values are published; anything that needs
  new source data needs `kapiti.yml` (T-82).
- **[`.github/workflows/sources.yml`](.github/workflows/sources.yml)**: a weekly check of every source's fields,
  record count and last-edit date. Snapshots go to the `source-checks` branch, and the run is flagged when anything
  changed, so a rebuild can be planned.
- **[`service/`](service/)**: a read-only MCP server over those results, run locally. Each value comes with its kind,
  sources, licence and fit-for-parcel flag. In public mode it serves only licence-cleared columns (D-12). It is not yet
  offered to outside users.
- **[`archive/prototype-2026-11/`](archive/prototype-2026-11/)**: the original 96-domain design prototype, kept for
  reference. Its data is fictional.

## What is planned

Tracked on [`TASKS.md`](TASKS.md): a fresh-eyes review of the query service before anyone outside uses it,
confirmation of the council licences (T-35), source-change checks (T-25), then one more council (T-24).

## Run one tile

```bash
cd pipeline
pip install pyproj shapely rasterio numpy duckdb pandas requests scipy
python3 fetch_tile.py data && python3 fetch_lidar.py data && python3 fetch_parcels_kcdc.py data
LINZ_API_KEY=... python3 fetch_parcels.py data     # titles and easements (free LINZ Data Service key)
python3 compile_tile.py data && python3 inverse_queries.py data
```

Set `TILE_XMIN` and `TILE_YMIN` (NZTM2000, metres) to choose another tile. Or run it on GitHub:

```bash
gh api -X POST repos/aashtonnz/land-query/actions/workflows/tile.yml/dispatches -f ref=main \
  -f 'inputs[xmin]=1769000' -f 'inputs[ymin]=5468400'
```

## Data and licences

All sources used so far are CC BY 4.0 (LINZ, Kāpiti Coast District Council, Greater Wellington Regional Council). See
[`SOURCES.md`](SOURCES.md) for each source's licence basis, update date and whether its values are fit for use at parcel
level. Owner names are not collected.
