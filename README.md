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
- **[`.github/workflows/kapiti.yml`](.github/workflows/kapiti.yml)**: compiles the whole Kāpiti Coast district (27,614
  parcels, 77 columns including computed sun, roof, flow and earthworks measures, 46 blocks) in about 40 minutes, with quality checks on every block, and pushes the merged parcel
  table and query results to the `kapiti-results` branch ([findings](docs/findings/2026-11-06-kapiti-district.md)).
- **[`archive/prototype-2026-11/`](archive/prototype-2026-11/)**: the original 96-domain design prototype, kept for
  reference. Its data is fictional.

## What is planned

Tracked on [`TASKS.md`](TASKS.md): a fresh-eyes review (T-39), a read-only MCP query
service on the compiled data (T-36), source-change checks (T-25), then one more council (T-24).

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
