# Plan

Full descriptions for open tasks in `Next` and `Planned` on [`TASKS.md`](TASKS.md).

## Next (Phase 1 — Live Kāpiti Coast Hydration & Verification)

- **T-16: Single-tile live Kāpiti test** (in progress)
  Scripts in [`pipeline/tile_test/`](pipeline/tile_test/) fetch KCDC zones, overlays, flood hazards and levels, three-waters assets, building outlines, GWRC liquefaction and slope failure, and LINZ 1 m DEM/DSM (2024–25) and DEM (2021) from the public `s3://nz-elevation` COGs, for the tile 1769000–1770000 E, 5468400–5469400 N. Remaining: LINZ parcels (layer 50823), titles (50804) and non-primary parcels (50782) via WFS, which needs `LINZ_API_KEY` (`fetch_parcels.py`).
- **T-33: Inverse query on live parcels**
  Recompile with parcels as the unit. Run a handful of region-wide inverse queries across the tile, each returning parcel rows with the source, date and licence of every value used. Compare with what Landsight's free MCP and Relab return for the same questions.
- **T-30: Replace invented benchmark fixtures**
  The benchmark records for 10 Tararua St, 16 Ngahina St and 114 Otaihanga Rd describe real addresses with invented physical, legal and ownership facts. Replace with clearly fictional addresses (or real fetched data) in the compiler, schemas and `index.html` before GitHub Pages or `llms.txt` publish anything.
- **T-31: Licence and resolution register**
  A table (for example `SOURCES.md`) with one row per source: owner, URL, licence and commercial-use terms, attribution text, update frequency, spatial resolution, and whether values are fit for parcel-level use. Starts from the licence notes in the T-16 findings.
- **T-29: Check LiDAR change candidates**
  For the 37 patches of ≥100 m² changed by more than 1 m between the 2021 and 2024–25 DEMs (after the +0.08 m systematic offset), compare against LINZ aerial imagery from both periods and classify each as earthworks, construction, vegetation or artefact.
- **T-32: Reset proposal**
  Using the sourceability audit, propose decision D-11 (product scope: a smaller schema of sourceable, licensed, privacy-safe domains with provenance and resolution on every value), the pruned schema, a restated T-17 gate as per-tile cost on GitHub Actions, and a revised board and plan. For approval before applying.
- **T-17: Gate: Single-tile compile speed and memory** (answered 2026-11-06; see Done)
- **T-18: Local statutory PDF parser test**
  Download 10 real public KCDC `s42A` officer reports and sample LIM PDFs and run `dredge_raw_statutory_text_zero_cost()` to verify extraction of `DP` numbers, `RM` consent IDs, rule breaches (`m`), `s95A` notification decisions, and imperial pipe depths (`ft/in` → `m`).
- **T-19: Gate: Statutory regex parser accuracy**
  Require `≥9/10` precision/recall on structured fields across the 10 sample KCDC PDFs. If unstructured prose paragraphs are missed, add an optional local Ollama (`qwen2.5-coder:7b`) extraction pass.
- **T-20: Sentinel-1 & Sentinel-2 STAC bounding-box test**
  Query `https://earth-search.aws.element84.com/v1/search` for Kāpiti (`MGRS 60GUV`), read windowed NIR (`B08`), Red (`B04`), and SWIR (`B11`) arrays via COG Range requests, and populate `D71` `NDVI`/`NDWI` columns.
- **T-21: Full Kāpiti Coast 54-tile batch compilation**
  Run the crash-resumable `1 km × 1 km` batch loop across all 54 populated Kāpiti Coast tiles (`~24,800` parcels), sealing each tile checkpoint in `tile_checkpoint_manifest`.
- **T-22: Cross-check audit on live Kāpiti data**
  Run the 15-pillar, 64-invariant cross-checker (`D79–D84`) over the compiled Kāpiti SQLite database to audit `Wgtn1953` vs `NZVD2016` manhole rim offsets and `Layer 101292` vs Council RID floor-area discrepancies.
- **T-23: Enable GitHub Pages and test Claude Desktop MCP connection**
  Enable GitHub Pages on `github.com/aashtonnz/land-query` and register `toponz_weekend1_kapiti_ingester.py --serve-mcp` in local `claude_desktop_config.json`.

## Planned (Phase 2 — Greater Wellington & National Scaling)

- **T-24: Expand tile batch compiler to Wellington City, Hutt Valley, and Porirua (`180,000` parcels)**
  Add WCC, HCC, UHCC, and PCC Three Waters and District Plan WFS endpoints to the tile batch compiler.
- **T-25: Build automated weekly GitHub Actions Watchtower probe script (`watchtower_cron.yml`)**
  Extend `.github/workflows/watchtower_cron.yml` to send live `HEAD`/`GET` requests to the 108 agency URLs (`/.well-known/mcp.json`, `/llms.txt`, `/data.json`) and commit any schema hash diffs.
- **T-26: Deploy Cloudflare Workers + D1 + R2 free-tier edge read replica**
  Push compiled SQLite shards to Cloudflare D1/R2 free tiers and expose the `POST /v1/contribute-lim` Give-to-Get PDF upload gate.

## Planned (Phase 3 — Trans-Tasman Federation)

- **T-27: Test live NSW Planning Portal and SixMaps WFS adapter**
  Run a single-tile test on Parramatta (NSW) mapping `Lot/DP`, `s10.7` planning certificates, and `s88B` easements into the 96-domain schema.
