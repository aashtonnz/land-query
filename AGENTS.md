# Instructions for AI agents (`land-query`)

This project follows [ai-working-practices](https://github.com/aashtonnz/ai-working-practices). Read its `README.md` at the start of every conversation, and check its `CHANGELOG.md` at least once a day in longer work.

## Practices followed

- **Task board**: v1.10 ([`TASKS.md`](TASKS.md), [`DECISIONS.md`](DECISIONS.md), [`PLAN.md`](PLAN.md))
- **Style guide**: v1 ([`STYLE.md`](STYLE.md))
- **Risk list**: v1.1 ([`RISKS.md`](RISKS.md))
- **Changelog checked to**: entry 33 (6 Nov 2026)

## Project rules

1. **Zero out-of-pocket budget (`$0.00`)**: Do not introduce paid APIs, paid cloud databases, or paid LLM token calls. Use open government WFS/REST/STAC endpoints, Shared-DP (Deposited Plan) deduplication, local SQLite WAL + FTS5, and local NumPy physics kernels.
2. **No external contact**: Never email, message, or contact external people, councils, or organisations.
3. **Keep what exists separate from what is planned**:
   - **What exists now**: The 96-domain schema (`2,746` primitives across 17 SQLite tables), the local Python compiler and JSON-RPC 2.0 MCP server (`toponz_weekend1_kapiti_ingester.py`) verified on Kāpiti Coast benchmark data (`10 Tararua St`, `16 Ngahina St`, `114 Otaihanga Rd`), and the 37-tab interactive reference UI (`index.html`).
   - **What is planned**: Live WFS/STAC bulk hydration across all 54 Kāpiti Coast `1 km × 1 km` tiles (`24,800` parcels) and broader NZ/AU regions (see [`TASKS.md`](TASKS.md) and [`PLAN.md`](PLAN.md)).
4. **Git**: agents may commit, push and merge to `main` without asking first (owner's standing permission, 2026-11-06). Work on a branch and merge when the change is complete and the board is updated.
5. **Raw facts + deterministic physics**: Store unopinionated statutory and physical primitives plus reproducible physics outputs (`SIM-01` to `SIM-12`) and cross-check reconciliation flags (`D79–D84`), rather than subjective scores.
