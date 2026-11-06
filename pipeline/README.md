# Pipeline

Scripts that fetch one 1 km × 1 km NZTM2000 tile from public sources and compile one row of facts per parcel into DuckDB.
The default tile is central Paraparaumu (1769000–1770000 E, 5468400–5469400 N); set `TILE_XMIN` and `TILE_YMIN` for another.
On GitHub, [`tile.yml`](../.github/workflows/tile.yml) runs all of this with the LINZ key from the repository secret. Results: [`docs/findings/2026-11-06-live-tile-test.md`](../docs/findings/2026-11-06-live-tile-test.md) and [`docs/findings/2026-11-06-inverse-queries.md`](../docs/findings/2026-11-06-inverse-queries.md).

```bash
pip install pyproj shapely rasterio numpy duckdb pandas requests scipy
python3 fetch_tile.py data          # KCDC and GWRC vector layers, provenance in data/provenance.json
python3 fetch_lidar.py data         # LINZ 1 m DEM/DSM windows (2024-25, 2021)
python3 fetch_parcels_kcdc.py data  # primary parcels from KCDC's public LINZ mirror (no key; D-11)
LINZ_API_KEY=... python3 fetch_parcels.py data   # LINZ parcels (for comparison), titles, easements (free LDS key)
python3 compile_tile.py data        # per-parcel primitives into data/tile.duckdb (parcels if fetched, else buildings)
python3 inverse_queries.py data     # five inverse queries with provenance into data/inverse_queries.json
```

Licences, fit-for-parcel flags and column definitions: [`SOURCES.md`](../SOURCES.md). Fetched data (`data/`) is not committed; it is reproducible from these scripts. Set `ONLY=name1,name2` to refetch
selected layers in `fetch_tile.py`.
