# Risks

Last updated: 2026-11-06 (Pacific/Auckland)
Follows: risk list v1.1 (ai-working-practices)

## R-1: Upstream WFS / LiDAR rate-limiting or memory exhaustion during bulk suburb compilation
**Why it matters.** Compiling all 24,800 Kāpiti Coast parcels from live LINZ Data Service WFS and `1m` LiDAR rasters on a single laptop could hit HTTP rate limits or exhaust RAM if full regional GeoTIFFs are loaded at once.
**What we can likely do.** Process one `1 km × 1 km` (`EPSG:2193`) tile at a time (`~450` parcels/tile) using HTTP Range requests on Cloud-Optimized GeoTIFFs (COGs) and save tile status in `tile_checkpoint_manifest` so interrupted runs resume cleanly.
**Early test.** Run live ingestion on one `1 km × 1 km` Paraparaumu tile (`NZTM-1760-5472`) and measure wall-clock time and peak RAM against the 5-second / 2 GB gate (`T-16`, `T-17`).

## R-2: Vertical datum mismatches (`Wellington 1953` vs `NZVD2016`) in council pipe invert data
**Why it matters.** A `0.38 m` vertical datum offset between legacy council manhole records and `NZVD2016` LiDAR can flip a gravity sewer feasibility calculation from pass to fail.
**What we can likely do.** Enforce Pillar 1 of the cross-checker (`D79`): compare every council manhole rim elevation (`D07`) against the `NZVD2016` `1m` LiDAR ground elevation (`D05`) at the manhole `(X, Y)` coordinates and auto-normalize systematic offsets before computing sewer gradients (`SIM-06`).
**Early test.** Audit manhole rim vs. LiDAR DEM offsets across all compiled Kāpiti tiles (`T-22`).

## R-3: OCR noise and non-standard formatting in scanned 1950s–1980s council PDFs
**Why it matters.** If the `$0.00` deterministic regex/AST parser (`dredge_raw_statutory_text_zero_cost`) misses handwritten or poorly scanned imperial pipe depths or `s221` notices, historical primitives (`D53`, `D54`) will be incomplete.
**What we can likely do.** Combine deterministic regex patterns for structured statutory tokens (`DP`, `RM`, `ft/in`, `s95A`, `s221`) with a local, zero-API-cost Ollama fallback (`qwen2.5-coder:7b`) for unstructured paragraphs.
**Early test.** Test the deterministic parser against 10 real downloaded KCDC `s42A` consent reports and LIM PDFs and check whether it hits the 9/10 accuracy gate (`T-18`, `T-19`).

## R-4: False positives in satellite SAR, thermal, and spectral indirect inferences (`D73–D75`)
**Why it matters.** Low-emissivity unpainted galvanized iron roofs (`ε ≈ 0.32`) appear artificially cold in thermal infrared, and steep terrain causes radar shadow/layover in Sentinel-1 InSAR, which could falsely flag or miss insulation and subsidence anomalies.
**What we can likely do.** Enforce Pillar 14 sensor de-biasing (`D84`): calibrate roof thermal brightness temperature using material emissivity classified from `5cm` RGBI + `1064nm` LiDAR intensity, and require a 4-of-5 multi-sensor quorum before flagging geotechnical or occupancy anomalies.
**Early test.** Fetch one live Sentinel-2 scene over Kāpiti from Element84 STAC (`T-20`) and run the 15-pillar cross-checker across live Kāpiti parcels (`T-22`).

## R-5: Cold-start gap on `$6` LINZ private covenant instrument PDFs
**Why it matters.** While free LINZ Layer 50804 tables expose the existence and instrument number of every covenant and `s221` consent notice, the verbatim text inside a private covenant PDF costs `$6` from LINZ if no sibling lot on that Deposited Plan (`DP`) has uploaded a title or LIM yet.
**What we can likely do.** Flag the exact instrument number and pre-2001 sunset status (`D02/D54`) from the free memorial table so agents know an encumbrance exists, and use the Shared-DP (`1:64`) Give-to-Get Vault (`POST /v1/contribute-lim`) so a single uploaded PDF hydrates all sibling lots on that `DP` plan.
**Early test.** Measure what percentage of Paraparaumu residential lots on `NZTM-1760-5472` share a Deposited Plan (`DP`) with at least 10 sibling lots (`T-16`).

## R-6: Silent schema changes or new AI/MCP endpoints launched by councils and agencies
**Why it matters.** If a council renames WFS fields or launches a new STAC/OGC/MCP endpoint, static scrapers can break or fall behind.
**What we can likely do.** Run the weekly GitHub Actions Watchtower (`watchtower_cron.yml`) to fingerprint `/.well-known/mcp.json`, `/llms.txt`, `/data.json` (DCAT-AP), and `FeatureServer?f=pjson` schemas across the 108 monitored agencies.
**Early test.** Execute the live HTTP HEAD/GET Watchtower sweep script in GitHub Actions (`T-25`).

## Settled
- R-7: Upfront `$300k` LINZ title document purchase cost: Settled by extracting instrument numbers from free LINZ Layer 50804 memorial tables and applying Shared-DP (`1:64`) instrument deduplication (`D-2`). 2026-11-05.
- R-8: `$18k/yr` cloud PostGIS and raster hosting cost: Settled by streaming `1m` LiDAR tiles in memory (`NumPy`), discarding raw rasters after extracting `1.8 KB/plot` physics primitives, and storing in local SQLite WAL + FTS5 (`D-2`, `D-3`). 2026-11-05.
