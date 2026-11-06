# Prototype, November 2026 (archived)

The original 96-domain design, built from the first Gemini conversation: a compiler and MCP server
(`toponz_weekend1_kapiti_ingester.py`), a 37-tab reference web page (`index.html`), schema catalogues (`schemas/`) and an
MCP manifest (`.well-known/mcp.json`).

Archived on 6 Nov 2026 by decision D-12 ([reset proposal](../../docs/proposals/2026-11-06-reset.md)). Kept for its ideas;
nothing builds on it.

**Its data is fictional.** The three benchmark parcels (10 Example St, 16 Sample St, 114 Specimen Rd) and every fact about
them, including parcel, plan, consent and title numbers and company names, are invented. Several of its domains are
dropped or deferred under D-12. Real data comes only from [`pipeline/`](../../pipeline/).

To run it: `python3 toponz_weekend1_kapiti_ingester.py --self-test` (from this folder).
