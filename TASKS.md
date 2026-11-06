# Tasks

Last updated: 2026-11-06 18:05 (Pacific/Auckland)
Follows: task board v1.10 (ai-working-practices), changelog to entry 33

Standing priorities:
- Keep out-of-pocket infrastructure and data cost at `$0.00`.
- Do not contact external people or organisations.
- Keep existing verified benchmark data clearly distinct from planned live bulk regional ingestion.
- Risk list: [`RISKS.md`](RISKS.md) | Decision log: [`DECISIONS.md`](DECISIONS.md) | Plan details: [`PLAN.md`](PLAN.md)

## Doing (at most 3)

## Waiting on you
- T-34: `LINZ_API_KEY` is still not visible in a new session (checked 2026-11-06 18:00), so it may not have been saved to this environment. Parcels no longer need it (D-11), but titles, easements, road and non-primary parcels do. Check the variable is set on the environment itself, then start a new session. Raised 2026-11-06.

## Next (in order, at most about 10)
- T-34: LINZ titles, easements and non-primary parcels: fetch layers 50804, 50782 and easements for the tile with `fetch_parcels.py` (needs the LINZ key, see Waiting on you), and compare the KCDC parcel mirror with LINZ to measure its lag.
- T-30: Replace invented benchmark fixtures: the three benchmark parcels use real addresses with invented facts (10 Tararua Street is really a 2,427 m² lot with one building). Replace with clearly fictional addresses or real fetched data before anything is published.
- T-31: Licence and resolution register: one entry per source with licence, commercial-use terms, attribution, update frequency and spatial resolution or fit-for-parcel flag, plus a plain definition of each compiled column (T-33 showed a misread flood level; confirm KCDC pipe condition grade 0 means not assessed) (early test for R-9 and R-10).
- T-29: Check LiDAR change candidates: 25 of the 30 changed parcels are recent subdivisions (T-33), so start with the other five; compare the 37 tile patches with more than 1 m of ground change (2021 to 2024–25, after the +0.08 m offset) against aerial imagery to tell earthworks from classification artefacts.
- T-32: Reset proposal: a proposed decision (D-12), restated Shared-DP assumption (about 3.7 lots per plan measured, not 1:64), pruned schema based on the sourceability audit, and revised board and plan, for approval before the repo is changed.
- T-18: Local statutory PDF parser test: Run the deterministic regex/AST parser (`dredge_raw_statutory_text_zero_cost`) on 10 real downloaded KCDC `s42A` officer reports and LIM PDFs (early test for R-3).
- T-19: Gate: Statutory regex parser accuracy: Does the deterministic parser extract DP numbers, rule breaches, and imperial pipe depths accurately on at least 9 of 10 real KCDC PDFs? If no: add a local Ollama (`qwen2.5-coder:7b`) fallback pass for unstructured paragraphs.
- T-20: Sentinel-1 & Sentinel-2 STAC bounding-box test: Fetch one real Sentinel-2 COG scene over Kāpiti (`60GUV`) from Element84 Earth Search STAC API (`earth-search.aws.element84.com/v1`) and verify `NDVI`/`NDWI` parcel clipping (early test for R-4).
- T-21: Full Kāpiti Coast 54-tile batch compilation: Run the crash-resumable tile batch compiler across all 54 Kāpiti tiles (`24,800` parcels) into local SQLite WAL + FTS5.
- T-22: Cross-check audit on live Kāpiti data: Run the 15-pillar cross-checker across the compiled Kāpiti database and inspect false-positive rate on datum offsets and building floor-area deltas (early test for R-5).
- T-23: Enable GitHub Pages and test Claude Desktop MCP connection: Point `claude_desktop_config.json` at `toponz_weekend1_kapiti_ingester.py --serve-mcp` and test live agent queries.

## Planned (after Next, by phase)
Phase 2 — Greater Wellington & National Scaling:
- T-24: Expand tile batch compiler to Wellington City, Hutt Valley, and Porirua (`180,000` parcels).
- T-25: Build automated weekly GitHub Actions Watchtower probe script (`watchtower_cron.yml`) to check live HTTP statuses across the 108 agency endpoints (early test for R-6).
- T-26: Deploy Cloudflare Workers + D1 + R2 free-tier edge read replica and `POST /v1/contribute-lim` Give-to-Get PDF upload endpoint.

Phase 3 — Trans-Tasman (NSW / VIC) Federation:
- T-27: Test live NSW Planning Portal and SixMaps WFS adapter on one Sydney suburb tile (`Parramatta`).

## Later / ideas
- Add local GNS Strong-Motion and GeoNet sensor PGA shake-map auto-ingestion after M4.5+ earthquakes.
- Build automated Section 32 / Section 33 Council Rating Valuation Objection letter generator from `cross_silo_contradictions_70d`.

## Done (last two weeks, newest first)
- T-33: Inverse query on live parcels: five region-wide queries (infill candidates, floor level above ground, old poor sewers, ground change, heritage and trees) over 472 parcels in under 0.2 s, every row with source URL, sha256, fetch time and licence. For Kāpiti, neither Landsight nor Relab can answer the first four. [Findings](docs/findings/2026-11-06-inverse-queries.md) 2026-11-06.
- T-16: Single-tile live Kāpiti test: 34 public sources, three LiDAR rasters and 582 parcels (keyless, from KCDC's LINZ mirror, D-11) fetched live and compiled on parcels. Titles and easements moved to T-34. [Findings](docs/findings/2026-11-06-live-tile-test.md) 2026-11-06.
- T-28: Competitor check on live tools: Landsight's free MCP offers address search and single-property fetch only; its own page for a Paraparaumu property says it holds no stormwater, wastewater or flood data outside Auckland, Christchurch and Hamilton. KCDC publishes all three openly. [Findings](docs/findings/2026-11-06-live-tile-test.md#competitor-comparison-landsight-verified-via-its-free-mcp-and-a-public-property-page) 2026-11-06.
- T-17: Gate answered — single-tile speed and memory: memory passes easily (253 MB peak); time fails as written (LiDAR 62 s, vectors 2–21 s per layer, compile 19 s), but it is network-bound, not compute-bound. Decision deferred to T-32: restate the gate as a per-tile cost on GitHub Actions. [Findings](docs/findings/2026-11-06-live-tile-test.md#performance-against-the-t-17-gate) 2026-11-06.
- T-15: Push initial commit: `main` is on GitHub at commit `b9cdd00`. [github.com/aashtonnz/land-query](https://github.com/aashtonnz/land-query) 2026-11-06.
- T-14: Align repository with `ai-working-practices`: Added `AGENTS.md`, `CLAUDE.md`, `TASKS.md`, `DECISIONS.md`, `RISKS.md`, `PLAN.md`, `STYLE.md`; `README.md` follows Style guide v1. [`AGENTS.md`](AGENTS.md) 2026-11-06.
- T-13: 3D strata, designations, TDRs & 12-class Crown estate (`D91–D96`): Added `advanced_mutations_zoning_and_crown_estate_96d` table and Tab 37. [`toponz_weekend1_kapiti_ingester.py`](toponz_weekend1_kapiti_ingester.py) 2026-11-06.
- T-12: Multi-generational farm-to-lot coordinate backfill (`D89–D90`): Added `ancestral_farm_to_lot_backfill_90d` table and 5-class inheritance algebra in Tab 36. [`schemas/ancestral_farm_to_lot_backfill_90d_report.json`](schemas/ancestral_farm_to_lot_backfill_90d_report.json) 2026-11-06.
- T-11: Cadastral split/join DAG, split-zoning slicer & non-private land (`D85–D88`): Added `cadastral_lineage_dag_85d`, `parcel_split_zoning_and_epochs_86d`, and `non_private_and_special_tenure_88d` in Tab 35. [`schemas/lineage_splitzoning_and_nonprivate_land_88d_report.json`](schemas/lineage_splitzoning_and_nonprivate_land_88d_report.json) 2026-11-06.
- T-10: Unified 1-call Master Dossier generator: Added `--dossier <parcel_id>` CLI and `toponz_generate_master_84d_dossier` MCP tool in Tab 34. [`schemas/master_84domain_unified_dossier.json`](schemas/master_84domain_unified_dossier.json) 2026-11-06.
- T-09: 15-pillar, 64-invariant multi-witness cross-checker (`D79–D84`): Added `plot_crosscheck_reconciliation_80d` table and Tab 33. [`schemas/exhaustive_15pillar_64invariant_crosscheck_report.json`](schemas/exhaustive_15pillar_64invariant_crosscheck_report.json) 2026-11-06.
- T-08: 6-modality, 36-signal indirect inference schema (`D73–D78`): Added `plot_indirect_inferences_78d` table and Tab 32. [`schemas/indirect_inference_78domain_deep_dive.json`](schemas/indirect_inference_78domain_deep_dive.json) 2026-11-06.
- T-07: Satellite EO fusion & 6-layer SVG visual X-ray (`D71–D72`): Added `plot_satellite_eo_and_visual_layers_72d` table and Tab 31. [`schemas/satellite_eo_and_visual_renderer_report.json`](schemas/satellite_eo_and_visual_renderer_report.json) 2026-11-06.
- T-06: `1 km × 1 km` tile checkpoint schema & cross-silo contradiction table: Added `tile_checkpoint_manifest` and `cross_silo_contradictions_70d` in Tab 30. [`schemas/bulk_tile_and_contradiction_arbitrage_report.json`](schemas/bulk_tile_and_contradiction_arbitrage_report.json) 2026-11-06.
- T-05: Natural resources sub-spine (`D65–D70`): Added `plot_natural_resources_70d` table (minerals, water takes, LUC/NPS-HPL, ETS carbon, solar/wind, esplanade strips) in Tab 29. [`schemas/natural_resources_70domain_report.json`](schemas/natural_resources_70domain_report.json) 2026-11-06.
- T-04: `1:N` building and unit sub-spine (`D59–D64`): Added `plot_buildings_and_units_64d` table (bedrooms, RID vs LiDAR floor delta, cladding, Healthy Homes, `%NBS`, `CCC`, relocation salvage) in Tab 28. [`schemas/building_64domain_subspine_report.json`](schemas/building_64domain_subspine_report.json) 2026-11-06.
- T-03: `$0.00` deterministic statutory regex/AST parser & 6-scenario agent evaluation benchmark: Added `dredge_raw_statutory_text_zero_cost()` and `run_agent_eval_benchmark()` in Tab 27. [`schemas/zero_contact_eval_and_dredger_report.json`](schemas/zero_contact_eval_and_dredger_report.json) 2026-11-05.
- T-02: Autonomous endpoint Watchtower schema: Added `watchtower_endpoint_registry` table and Tab 26. [`schemas/ecosystem_watchtower_report.json`](schemas/ecosystem_watchtower_report.json) 2026-11-05.
- T-01: Core 58-domain schema, 12 vectorized NumPy physics kernels (`SIM-01` to `SIM-12`), Shared-DP deduplication model, and standalone SQLite/MCP compiler: Built `toponz_weekend1_kapiti_ingester.py` and Tabs 1–25. [`toponz_weekend1_kapiti_ingester.py`](toponz_weekend1_kapiti_ingester.py) 2026-11-05.
