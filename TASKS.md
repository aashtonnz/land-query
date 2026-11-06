# Tasks

Last updated: 2026-11-06 (Pacific/Auckland)
Follows: task board v1.9 (ai-working-practices), changelog to entry 32

Standing priorities:
- Keep out-of-pocket infrastructure and data cost at `$0.00`.
- Do not contact external people or organisations.
- Keep existing verified benchmark data clearly distinct from planned live bulk regional ingestion.
- Risk list: [`RISKS.md`](RISKS.md) | Decision log: [`DECISIONS.md`](DECISIONS.md) | Plan details: [`PLAN.md`](PLAN.md)

## Doing (at most 3)
- T-14: Align repository with `ai-working-practices`: Add `AGENTS.md`, `CLAUDE.md`, `TASKS.md`, `DECISIONS.md`, `RISKS.md`, `PLAN.md`, and `STYLE.md`, and rewrite `README.md` to follow Style guide v1.

## Waiting on you
- T-15: Push initial commit to `github.com/aashtonnz/land-query`: The sandbox VM has no outbound internet access, so it cannot run `git push` directly. Suggested: unzip `land-query-v39.0-repo.zip` locally and run `cd land-query && git push -u origin main`. Raised 2026-11-06.

## Next (in order, at most about 10)
- T-16: Single-tile live Kāpiti WFS & LiDAR test: Run a live fetch script on your machine for one `1 km × 1 km` Paraparaumu tile (`NZTM-1760-5472`, ~462 parcels) against LINZ Data Service WFS and GWRC Open Data (early test for R-1 and R-2).
- T-17: Gate: Single-tile compile speed and memory: Does one live `1 km × 1 km` tile compile in under 5 seconds and under 2 GB RAM on a laptop? If no: switch LiDAR raster reads to HTTP Range-request Cloud-Optimized GeoTIFF (COG) windows before running all 54 Kāpiti tiles.
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
