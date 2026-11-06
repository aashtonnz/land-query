# Tasks

Last updated: 2026-11-06 20:15 (Pacific/Auckland)
Follows: task board v1.10 (ai-working-practices), changelog to entry 33

Standing priorities:
- Keep out-of-pocket infrastructure and data cost at `$0.00`.
- Do not contact external people or organisations.
- Keep what exists (the pipeline, tested on one tile) clearly distinct from what is planned. Scope per D-12.
- Risk list: [`RISKS.md`](RISKS.md) | Decision log: [`DECISIONS.md`](DECISIONS.md) | Plan details: [`PLAN.md`](PLAN.md) | Sources: [`SOURCES.md`](SOURCES.md)

## Doing (at most 3)

## Waiting on you
- T-35: Confirm KCDC and GWRC licences in writing: 12 of the 23 source rows rely on a portal-wide CC BY 4.0 statement rather than a licence on the dataset (see [`SOURCES.md`](SOURCES.md)). Before anything is sold, ask each council's GIS team to confirm the statement covers the uncatalogued service layers. Only you can make that contact. Raised 2026-11-06.

## Next (in order, at most about 10)
- T-21: Full Kāpiti compile (in progress: 46 blocks of 5 km, `kapiti.yml`): run `tile.yml` over every tile that overlaps the district and merge the results into one database, with QA checks on every tile (manhole lids and building ground heights against LiDAR, LiDAR epoch offset, parcel areas against LINZ).
- T-37: Cheap computed measures: add sun hours and winter shading, horizon and view angles, overland flow and catchment, roof planes and solar potential, cut/fill for a level platform, and an approximate wind exposure category; check each once against something independent; mark every column published, derived or modelled in `SOURCES.md`.
- T-39: Fresh-eyes review: a new session, starting from the code, `SOURCES.md` and D-12 rather than earlier summaries, reviews the pipeline and the query results for errors before T-36 is offered to anyone outside. Fixes come with a check that fails before and passes after.
- T-36: Query service: a read-only MCP server on the compiled Kāpiti database that answers area queries with provenance, licence, value kind and fit-for-parcel flag on each row. Serve only licence-cleared data to outside users (T-35).
- T-29: Check LiDAR change candidates: five changed parcels not explained by recent subdivisions (T-33), checked against LINZ 7.5 cm aerials from both periods.
- T-25: Source-change checks: weekly workflow that records each source layer's fields and record count and flags changes.
- T-24: Second council: one adapter (Porirua or Wellington City) to measure the per-council cost before the rest of the region.

## Planned (after Next, by phase)
Phase 2 — Greater Wellington:
- T-38: Rest of Greater Wellington: Wellington City, Hutt, Upper Hutt and Porirua, once T-24 shows the adapter cost.

## Later / ideas
- T-18, T-19: Statutory PDF parser test and accuracy gate (deferred with consents and plan text, D-12).
- T-20: Sentinel-1/2 as labelled area context (not parcel facts).
- T-26: Hosted read replica (for example Cloudflare free tier); document uploads deferred for privacy and licence reasons.
- T-27: NSW adapter (Trans-Tasman).
- Deferred domains (one task each when picked up): plan rule text, issued consents, power and fibre, geotech (NZGD, S-map), current valuations, historic aerials, groundwater and water takes, LUC, Māori land (Pātaka Whenua terms), parcel lineage, census and schools, traffic counts; sale prices and building interiors once a lawful source exists.
- Deferred measures needing data we lack: road noise, driveway swept paths, CPT-based liquefaction, stereo fill reconstruction.
- GNS strong-motion and GeoNet shake-map ingestion after M4.5+ earthquakes.

## Done (last two weeks, newest first)
- T-32: Reset applied: decision D-12 (product scope), keep/defer/drop schema, corrected assumptions, prototype archived, pipeline moved to `pipeline/`, README, `llms.txt`, `AGENTS.md` and `STYLE.md` rewritten, board revised. [Proposal](docs/proposals/2026-11-06-reset.md) 2026-11-06.
- T-31: Licence and resolution register: [`SOURCES.md`](SOURCES.md) lists every source with licence, update date, fit-for-parcel flag and notes, plus a plain definition of every compiled column. Every source is CC BY 4.0: LINZ directly, KCDC through its open data portal (11 rows with a dataset licence, 12 on the portal statement), and GWRC through its regional statement. GWRC liquefaction is flagged as not fit for parcel use. Also fixed: the compiler now uses only in-use council pipes and manholes (results unchanged). KCDC condition grade 0 has no published definition. [`SOURCES.md`](SOURCES.md) 2026-11-06.
- T-30: Replace invented benchmark fixtures: the three benchmark parcels are now fictional (10 Example St, 16 Sample St, 114 Specimen Rd), along with 15 other real street addresses, invented companies with plausible names and one real consultancy. Parcel ids carry a `DEMO-` prefix, and plan, consent and title numbers sit in never-issued ranges (for example DP 9924819), so the parser still reads them. 1,956 replacements across the compiler, both HTML copies, 16 schemas, README and `llms.txt`; self-test output unchanged apart from the renames. A fictional-data notice is shown on the page, in `llms.txt` and in the README; `AGENTS.md` now forbids invented facts about real places, companies or people. Left as is: real town and school names (for example Paraparaumu College) used as context. 2026-11-06.
- Tile workflow on GitHub Actions: `.github/workflows/tile.yml` fetches, compiles and queries any tile using the `LINZ_API_KEY` repository secret; first run matched the local results exactly (2.5 min end to end, compile 12 s, 274 MB peak). [Workflow](.github/workflows/tile.yml) 2026-11-06.
- T-34: LINZ titles, easements and non-primary parcels: 667 titles (type only, no owners), 322 easements and 6 land covenants joined to the tile's parcels. KCDC's mirror matches LINZ exactly for the 582 shared parcels, shows no lag, and omits only railway parcels. Key supplied in chat for this run only and not stored; sessions started from the Claude app do not get Claude Code environment variables. [Findings](docs/findings/2026-11-06-inverse-queries.md#parcels-without-a-linz-key) 2026-11-06.
- T-33: Inverse query on live parcels: five region-wide queries (infill candidates, floor level above ground, old poor sewers, ground change, heritage and trees) over 472 parcels in under 0.2 s, every row with source URL, sha256, fetch time and licence. For Kāpiti, neither Landsight nor Relab can answer the first four. [Findings](docs/findings/2026-11-06-inverse-queries.md) 2026-11-06.
- T-16: Single-tile live Kāpiti test: 34 public sources, three LiDAR rasters and 582 parcels (keyless, from KCDC's LINZ mirror, D-11) fetched live and compiled on parcels. Titles and easements moved to T-34. [Findings](docs/findings/2026-11-06-live-tile-test.md) 2026-11-06.
- T-28: Competitor check on live tools: Landsight's free MCP offers address search and single-property fetch only; its own page for a Paraparaumu property says it holds no stormwater, wastewater or flood data outside Auckland, Christchurch and Hamilton. KCDC publishes all three openly. [Findings](docs/findings/2026-11-06-live-tile-test.md#competitor-comparison-landsight-verified-via-its-free-mcp-and-a-public-property-page) 2026-11-06.
- T-17: Gate answered — single-tile speed and memory: memory passes easily (253 MB peak); time fails as written (LiDAR 62 s, vectors 2–21 s per layer, compile 19 s), but it is network-bound, not compute-bound. Decision deferred to T-32: restate the gate as a per-tile cost on GitHub Actions. [Findings](docs/findings/2026-11-06-live-tile-test.md#performance-against-the-t-17-gate) 2026-11-06.
- T-15: Push initial commit: `main` is on GitHub at commit `b9cdd00`. [github.com/aashtonnz/land-query](https://github.com/aashtonnz/land-query) 2026-11-06.
- T-14: Align repository with `ai-working-practices`: Added `AGENTS.md`, `CLAUDE.md`, `TASKS.md`, `DECISIONS.md`, `RISKS.md`, `PLAN.md`, `STYLE.md`; `README.md` follows Style guide v1. [`AGENTS.md`](AGENTS.md) 2026-11-06.
- T-13: 3D strata, designations, TDRs & 12-class Crown estate (`D91–D96`): Added `advanced_mutations_zoning_and_crown_estate_96d` table and Tab 37. [`toponz_weekend1_kapiti_ingester.py` (archived)](archive/prototype-2026-11/toponz_weekend1_kapiti_ingester.py) 2026-11-06.
- T-12: Multi-generational farm-to-lot coordinate backfill (`D89–D90`): Added `ancestral_farm_to_lot_backfill_90d` table and 5-class inheritance algebra in Tab 36. [`schemas/ancestral_farm_to_lot_backfill_90d_report.json`](archive/prototype-2026-11/schemas/ancestral_farm_to_lot_backfill_90d_report.json) 2026-11-06.
- T-11: Cadastral split/join DAG, split-zoning slicer & non-private land (`D85–D88`): Added `cadastral_lineage_dag_85d`, `parcel_split_zoning_and_epochs_86d`, and `non_private_and_special_tenure_88d` in Tab 35. [`schemas/lineage_splitzoning_and_nonprivate_land_88d_report.json`](archive/prototype-2026-11/schemas/lineage_splitzoning_and_nonprivate_land_88d_report.json) 2026-11-06.
- T-10: Unified 1-call Master Dossier generator: Added `--dossier <parcel_id>` CLI and `toponz_generate_master_84d_dossier` MCP tool in Tab 34. [`schemas/master_84domain_unified_dossier.json`](archive/prototype-2026-11/schemas/master_84domain_unified_dossier.json) 2026-11-06.
- T-09: 15-pillar, 64-invariant multi-witness cross-checker (`D79–D84`): Added `plot_crosscheck_reconciliation_80d` table and Tab 33. [`schemas/exhaustive_15pillar_64invariant_crosscheck_report.json`](archive/prototype-2026-11/schemas/exhaustive_15pillar_64invariant_crosscheck_report.json) 2026-11-06.
- T-08: 6-modality, 36-signal indirect inference schema (`D73–D78`): Added `plot_indirect_inferences_78d` table and Tab 32. [`schemas/indirect_inference_78domain_deep_dive.json`](archive/prototype-2026-11/schemas/indirect_inference_78domain_deep_dive.json) 2026-11-06.
- T-07: Satellite EO fusion & 6-layer SVG visual X-ray (`D71–D72`): Added `plot_satellite_eo_and_visual_layers_72d` table and Tab 31. [`schemas/satellite_eo_and_visual_renderer_report.json`](archive/prototype-2026-11/schemas/satellite_eo_and_visual_renderer_report.json) 2026-11-06.
- T-06: `1 km × 1 km` tile checkpoint schema & cross-silo contradiction table: Added `tile_checkpoint_manifest` and `cross_silo_contradictions_70d` in Tab 30. [`schemas/bulk_tile_and_contradiction_arbitrage_report.json`](archive/prototype-2026-11/schemas/bulk_tile_and_contradiction_arbitrage_report.json) 2026-11-06.
- T-05: Natural resources sub-spine (`D65–D70`): Added `plot_natural_resources_70d` table (minerals, water takes, LUC/NPS-HPL, ETS carbon, solar/wind, esplanade strips) in Tab 29. [`schemas/natural_resources_70domain_report.json`](archive/prototype-2026-11/schemas/natural_resources_70domain_report.json) 2026-11-06.
- T-04: `1:N` building and unit sub-spine (`D59–D64`): Added `plot_buildings_and_units_64d` table (bedrooms, RID vs LiDAR floor delta, cladding, Healthy Homes, `%NBS`, `CCC`, relocation salvage) in Tab 28. [`schemas/building_64domain_subspine_report.json`](archive/prototype-2026-11/schemas/building_64domain_subspine_report.json) 2026-11-06.
- T-03: `$0.00` deterministic statutory regex/AST parser & 6-scenario agent evaluation benchmark: Added `dredge_raw_statutory_text_zero_cost()` and `run_agent_eval_benchmark()` in Tab 27. [`schemas/zero_contact_eval_and_dredger_report.json`](archive/prototype-2026-11/schemas/zero_contact_eval_and_dredger_report.json) 2026-11-05.
- T-02: Autonomous endpoint Watchtower schema: Added `watchtower_endpoint_registry` table and Tab 26. [`schemas/ecosystem_watchtower_report.json`](archive/prototype-2026-11/schemas/ecosystem_watchtower_report.json) 2026-11-05.
- T-01: Core 58-domain schema, 12 vectorized NumPy physics kernels (`SIM-01` to `SIM-12`), Shared-DP deduplication model, and standalone SQLite/MCP compiler: Built `toponz_weekend1_kapiti_ingester.py` and Tabs 1–25. [`toponz_weekend1_kapiti_ingester.py` (archived)](archive/prototype-2026-11/toponz_weekend1_kapiti_ingester.py) 2026-11-05.

Retired IDs: T-22 (replaced by QA checks in T-21), T-23 (replaced by T-36). Dropped: valuation objection letter generator (built on dropped domains).
