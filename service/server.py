"""MCP server for the Kāpiti Coast parcel results (T-36). Read-only.

Run: LANDQ_RESULTS=/path/to/results LANDQ_AUDIENCE=public python3 server.py   (stdio transport)
LANDQ_RESULTS holds the files published on the `kapiti-results` branch (see fetch_results.py). LANDQ_AUDIENCE is
"public" (default: only columns whose sources all carry a dataset licence) or "internal" (everything, for the owner).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp.server.mcpserver import MCPServer
from landquery import LandQuery, QueryError

LQ = LandQuery(os.environ.get("LANDQ_RESULTS", "results"), os.environ.get("LANDQ_AUDIENCE", "public"))
mcp = MCPServer(
    name="land-query",
    instructions=("Parcel facts for the Kāpiti Coast District, New Zealand, compiled from public LINZ, KCDC and GWRC data. "
                  "Every response lists, for each column, its kind (published, derived or modelled), meaning, sources, "
                  "fit-for-parcel flag and licence status, and for each source the sha256 and fetch time of the data "
                  "each row's block was compiled from. Coordinates are NZTM2000 metres. Start with `about`, then "
                  "`columns`. Derived and modelled values are estimates; say so when you pass them on."),
)


def _call(f, *a, **k):
    try: return f(*a, **k)
    except QueryError as e: return {"error": str(e)}


@mcp.tool(description="What the data is, which run it comes from, the audience mode and licence notes.")
def about() -> dict:
    return LQ.about()


@mcp.tool(description="Columns with their kind, meaning, sources, fit-for-parcel flag, licence status and whether they are served. Optional `contains` filters by name or meaning.")
def columns(contains: str | None = None) -> dict:
    return LQ.describe_columns(contains)


@mcp.tool(description="One parcel by LINZ parcel id (`unit_id`) or exact appellation (for example 'Lot 2 DP 58242'), with every served column and its provenance. `columns` limits the columns returned.")
def parcel(unit_id: int | None = None, appellation: str | None = None, columns: list[str] | None = None) -> dict:
    return _call(LQ.parcel, unit_id, appellation, columns)


@mcp.tool(description=("Parcels in an area and/or matching filters. `bbox` is [xmin, ymin, xmax, ymax] in NZTM2000 metres (at most 20 km "
                       "across). `where` is a list of {column, op, value}; ops: =, !=, <, <=, >, >=, in, is_null, not_null, contains, "
                       "and has_class for overlay columns (value: a class name, or {class, min_pct}). Up to 500 rows per call; page "
                       "with `offset`. `columns` limits the columns returned."))
def search(bbox: list[float] | None = None, where: list[dict] | None = None, columns: list[str] | None = None,
           limit: int = 100, offset: int = 0) -> dict:
    return _call(LQ.search, bbox, where, columns, limit, offset)


@mcp.tool(description="A precomputed district query (Q1 to Q5: infill candidates, high floor levels, old poor sewers, ground change, heritage and trees) with its SQL, rows and provenance.")
def query(id: str) -> dict:
    return _call(LQ.inverse_query, id)


if __name__ == "__main__":
    mcp.run("stdio")
