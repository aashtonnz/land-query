# Risks

Last updated: 2026-11-06 20:00 (Pacific/Auckland)
Follows: risk list v1.1 (ai-working-practices)

## R-9: Licences that do not permit commercial reuse
**Why it matters.** The product is to be sold. Some sources are non-commercial (S-map, GNS active faults), some have registration terms (NZGD), and several KCDC layers state no licence at all. Building on a source that cannot be resold means rework or legal exposure later.
**Update 2026-11-06 (D-12).** Collecting is not limited to licensed sources; the licence gates only what is served to outside users, so every value must carry its licence through to the query service (T-36).
**What we can likely do.** Keep a licence register and admit a source to the product only when its terms allow commercial redistribution; use council fault and hazard overlays instead of restricted national datasets; ask councils to confirm licences (a person, not an agent, makes that contact).
**Early test.** Done for the tile (T-31, 2026-11-06, [`SOURCES.md`](SOURCES.md)): all 23 source rows are CC BY 4.0. 11 carry the licence on the dataset; 12 rely on a portal-wide KCDC or GWRC statement. The council's 2012 map-viewer terms (viewing only) conflict on their face but cover the viewer website. Remaining step: written confirmation from KCDC and GWRC (T-35, owner only). Still open for every new council and for sources outside the tile (S-map, NZGD, GNS faults).

## R-10: Coarse data presented as parcel-level fact
**Why it matters.** Some layers are regional (GWRC liquefaction in the tile is one 32 km² polygon from 1:250,000 geology) while others are point-dense. An agent given an overlap percentage cannot tell the difference, and a confident wrong answer about a property is the fastest way to lose trust.
**What we can likely do.** Record spatial resolution and a fit-for-parcel flag for every source, and return them alongside every value.
**Early test.** Done (T-31): fit-for-parcel flags and plain column definitions are in [`SOURCES.md`](SOURCES.md); GWRC liquefaction is flagged not fit for parcel use. Not yet returned with each query row: carry the flag in `inverse_queries.json` provenance (T-32).

## R-1: Upstream WFS / LiDAR rate-limiting or memory exhaustion during bulk suburb compilation
**Why it matters.** Compiling all 24,800 Kāpiti Coast parcels from live LINZ Data Service WFS and `1m` LiDAR rasters on a single laptop could hit HTTP rate limits or exhaust RAM if full regional GeoTIFFs are loaded at once.
**What we can likely do.** Process one `1 km × 1 km` (`EPSG:2193`) tile at a time (`~450` parcels/tile) using HTTP Range requests on Cloud-Optimized GeoTIFFs (COGs) and save tile status in `tile_checkpoint_manifest` so interrupted runs resume cleanly.
**Early test.** Done for one tile (T-16, T-17, 2026-11-06): 253 MB peak, no rate limiting from KCDC or LINZ S3; two transient connection resets handled by retries. Time is network-bound (about 2 minutes per tile end to end). Still open at scale: full Kāpiti compile (T-21).

## R-3: OCR noise and non-standard formatting in scanned 1950s–1980s council PDFs
**Update 2026-11-06.** Parked: the PDF parser work is deferred with consents and plan text (D-12). Reopen when T-18 comes back.
**Why it matters.** If the `$0.00` deterministic regex/AST parser (`dredge_raw_statutory_text_zero_cost`) misses handwritten or poorly scanned imperial pipe depths or `s221` notices, historical primitives (`D53`, `D54`) will be incomplete.
**What we can likely do.** Combine deterministic regex patterns for structured statutory tokens (`DP`, `RM`, `ft/in`, `s95A`, `s221`) with a local, zero-API-cost Ollama fallback (`qwen2.5-coder:7b`) for unstructured paragraphs.
**Early test.** Test the deterministic parser against 10 real downloaded KCDC `s42A` consent reports and LIM PDFs and check whether it hits the 9/10 accuracy gate (`T-18`, `T-19`).

## R-4: False positives in satellite SAR, thermal, and spectral indirect inferences (`D73–D75`)
**Update 2026-11-06.** Restated by D-12: satellite values are only ever labelled area context, never parcel facts, which limits the damage. The remaining risk is an agent over-reading area context; carry the fit-for-parcel flag on every row (T-36).
**Why it matters.** Low-emissivity unpainted galvanized iron roofs (`ε ≈ 0.32`) appear artificially cold in thermal infrared, and steep terrain causes radar shadow/layover in Sentinel-1 InSAR, which could falsely flag or miss insulation and subsidence anomalies.
**What we can likely do.** Enforce Pillar 14 sensor de-biasing (`D84`): calibrate roof thermal brightness temperature using material emissivity classified from `5cm` RGBI + `1064nm` LiDAR intensity, and require a 4-of-5 multi-sensor quorum before flagging geotechnical or occupancy anomalies.
**Early test.** Fetch one live Sentinel-2 scene over Kāpiti from Element84 STAC (`T-20`) and run the 15-pillar cross-checker across live Kāpiti parcels (`T-22`).

## R-5: Cold-start gap on `$8` LINZ private covenant instrument PDFs
**Why it matters.** While free LINZ Layer 50804 tables expose the existence and instrument number of every covenant and `s221` consent notice, the verbatim text inside a private covenant PDF costs `$8` from LINZ (search fee since February 2025) if no sibling lot on that Deposited Plan (`DP`) has uploaded a title or LIM yet.
**What we can likely do.** v1 (D-12): record that each instrument exists, with its type and number, and don't claim its contents; buy text only where a query needs it. Earlier idea: flag the exact instrument number and pre-2001 sunset status (`D02/D54`) from the free memorial table so agents know an encumbrance exists, and use the Shared-DP (`1:64`) Give-to-Get Vault (`POST /v1/contribute-lim`) so a single uploaded PDF hydrates all sibling lots on that `DP` plan.
**Early test.** Done for one tile (T-33, 2026-11-06): 457 residential parcels on 124 plans (about 3.7 lots per plan); 38% on a plan with 10 or more lots in the tile, 93% sharing a plan with at least one other lot (lower bounds; plans cut by the tile edge are undercounted). Sharing helps but is far from 1:64, so the risk stands; D-2's assumption is to be restated in T-32.

## R-6: Silent schema changes or new AI/MCP endpoints launched by councils and agencies
**Update 2026-11-06.** Narrowed by D-12 to changes in the sources we use (about 40 layers): weekly checks of fields and record counts (T-25).
**Why it matters.** If a council renames WFS fields or launches a new STAC/OGC/MCP endpoint, static scrapers can break or fall behind.
**What we can likely do.** Run the weekly GitHub Actions Watchtower (`watchtower_cron.yml`) to fingerprint `/.well-known/mcp.json`, `/llms.txt`, `/data.json` (DCAT-AP), and `FeatureServer?f=pjson` schemas across the 108 monitored agencies.
**Early test.** Execute the live HTTP HEAD/GET Watchtower sweep script in GitHub Actions (`T-25`).

## R-2: Vertical datum mismatches (`Wellington 1953` vs `NZVD2016`) in council pipe invert data
**Why it matters.** A `0.38 m` vertical datum offset between legacy council manhole records and `NZVD2016` LiDAR can flip a gravity sewer feasibility calculation from pass to fail.
**Update 2026-11-06.** KCDC publishes every invert, cover level and flood level in both NZVD2016 and Wellington 1953 (T-16), so for Kāpiti the risk is settled at source. It remains for councils that publish one datum only; check each council when it is added (T-24).
**What we can likely do.** Enforce Pillar 1 of the cross-checker (`D79`): compare every council manhole rim elevation (`D07`) against the `NZVD2016` `1m` LiDAR ground elevation (`D05`) at the manhole `(X, Y)` coordinates and auto-normalize systematic offsets before computing sewer gradients (`SIM-06`).
**Early test.** Audit manhole rim vs. LiDAR DEM offsets across all compiled Kāpiti tiles (`T-22`).

## Settled
- R-7: Upfront `$300k` LINZ title document purchase cost: was settled on the 1:64 Shared-DP assumption (D-2); reopened 2026-11-06 when reuse measured about 3.7 lots per plan, and merged into R-5. v1 records that an instrument exists without buying its text (D-12).
- R-8: `$18k/yr` cloud PostGIS and raster hosting cost: Settled by streaming `1m` LiDAR tiles in memory (`NumPy`), discarding raw rasters after extracting `1.8 KB/plot` physics primitives, and storing in local SQLite WAL + FTS5 (`D-2`, `D-3`). 2026-11-05.
