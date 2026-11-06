# Instructions for AI agents (`land-query`)

This project follows [ai-working-practices](https://github.com/aashtonnz/ai-working-practices). Read its `README.md` at the start of every conversation, and check its `CHANGELOG.md` at least once a day in longer work.

## Practices followed

- **Task board**: v1.10 ([`TASKS.md`](TASKS.md), [`DECISIONS.md`](DECISIONS.md), [`PLAN.md`](PLAN.md))
- **Style guide**: v1 ([`STYLE.md`](STYLE.md))
- **Risk list**: v1.1 ([`RISKS.md`](RISKS.md))
- **Changelog checked to**: entry 33 (6 Nov 2026)

## Project rules

1. **Zero out-of-pocket budget (`$0.00`)**: Do not introduce paid APIs, paid cloud databases, or paid LLM token calls. Use open government WFS/REST/STAC endpoints, GitHub Actions free runners, and local Python (DuckDB, NumPy, Shapely, Rasterio).
2. **No external contact**: Never email, message, or contact external people, councils, or organisations.
3. **Keep what exists separate from what is planned**:
   - **What exists now**: the live pipeline (`pipeline/`, real public data with provenance), run per tile by `.github/workflows/tile.yml` and tested on one Paraparaumu tile; the licence and column register (`SOURCES.md`). The original prototype is in `archive/prototype-2026-11/` and its data is fictional.
   - **What is planned**: the rest of Kāpiti Coast, a query service, then other councils (see [`TASKS.md`](TASKS.md) and [`PLAN.md`](PLAN.md)).
   - **Scope (D-12)**: collect anything lawful whose source terms allow automated use; serve only licence-cleared data to outside users; mark each value published, derived or modelled; facts and inferences about land and buildings, never people; nothing invented. Never put invented facts against a real address, parcel, plan, title, consent, company or person.
4. **Git**: agents may commit, push and merge to `main` without asking first (owner's standing permission, 2026-11-06). Work on a branch and merge when the change is complete and the board is updated.
5. **Secrets and heavy runs**: the LINZ key is the `LINZ_API_KEY` repository secret on GitHub, not a session variable. Run data fetches and tile compiles through `.github/workflows/tile.yml` (start it with `gh api -X POST repos/aashtonnz/land-query/actions/workflows/tile.yml/dispatches -f ref=main -f 'inputs[xmin]=…' -f 'inputs[ymin]=…'`; results land on the `tile-results` branch). Never ask for the key in chat.
6. **Raw facts + deterministic physics**: Store unopinionated statutory and physical primitives plus reproducible physics outputs (`SIM-01` to `SIM-12`) and cross-check reconciliation flags (`D79–D84`), rather than subjective scores.
