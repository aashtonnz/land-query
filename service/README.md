# Query service

A read-only MCP server over the compiled Kāpiti Coast results (T-36). It answers parcel, area and filter queries, and
serves the five precomputed district queries. Every response gives, for each column, its kind (published, derived or
modelled), meaning, sources, fit-for-parcel flag and licence status. For each source it gives the dataset, URL, licence,
and the sha256 and fetch time of the data each row's block was compiled from. All of this comes from `SOURCES.md` and the
run's `provenance.json`.

## Run it locally

```bash
pip install -r service/requirements.txt
python3 service/fetch_results.py service/results
LANDQ_RESULTS=service/results LANDQ_AUDIENCE=internal python3 service/server.py
```

To use it from Claude Code:

```bash
claude mcp add land-query --env LANDQ_RESULTS=$PWD/service/results --env LANDQ_AUDIENCE=internal -- python3 $PWD/service/server.py
```

## Audience

- **`public`** (the default) serves only columns whose every source has a licence stated on the dataset. Columns that
  rely on a council's portal-wide statement are withheld, and cannot be filtered on, until the councils confirm in
  writing (T-35, D-12).
- **`internal`** serves everything, for the owner. Don't expose it to outside users.

## Tools

| Tool | What it does |
| --- | --- |
| `about` | Dataset, run and commit, audience, licence notes |
| `columns` | Each column's kind, meaning, sources, fit flag, licence status and whether it is served |
| `parcel` | One parcel by LINZ parcel id or exact appellation |
| `search` | Parcels in a bounding box (NZTM2000, at most 20 km across) and/or matching filters; up to 500 rows per call |
| `query` | Q1 to Q5 with their SQL, rows and provenance |

Filters are a list of `{column, op, value}`. The ops are `=`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `is_null`, `not_null` and
`contains`. Overlay columns also take `has_class`, with a class name or `{class, min_pct}`. Column names are checked
against the catalogue and values are passed as parameters, so a query cannot run arbitrary SQL.

## Tests

```bash
LANDQ_RESULTS=service/results python3 service/test_service.py
```

The district workflow runs these against each new set of results before publishing. It stops if any compiled column is
missing from `SOURCES.md` or from the catalogue in `catalogue.py`.
