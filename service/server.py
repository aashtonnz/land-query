"""MCP server for the Kāpiti Coast parcel results (T-36). Read-only.

Run: LANDQ_RESULTS=/path/to/results LANDQ_AUDIENCE=public python3 server.py   (stdio transport; LANDQ_TRANSPORT=http
serves MCP over HTTP at /mcp on PORT, with a per-address rate limit, for hosting: see http_app)
LANDQ_RESULTS holds the files published on the council's `<council>-results` branch (see fetch_results.py); COUNCIL
(default kapiti) names the council, and the service refuses another council's results (T-87). LANDQ_AUDIENCE is
"public" (default: only columns whose sources all carry a dataset licence) or "internal" (everything, for the owner).

The national index (T-102): `python3 prepare_national.py INDEX_DIR results` on a national build or release (index.parquet,
provenance.json, run.json), then LANDQ_RESULTS=results as above; the service sees it is national and uses the national
sources and columns in SOURCES.md, whatever COUNCIL is.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp.server.mcpserver import MCPServer
from landquery import LandQuery, QueryError
import catalogue as cat

LQ = LandQuery(os.environ.get("LANDQ_RESULTS", "results"), os.environ.get("LANDQ_AUDIENCE", "public"))
PROVENANCE = ("for each source the address, feature count and fetch time of the data each row's 40 km tile was built "
              "from" if LQ.national else "for each source the sha256 and fetch time of the data each row's block was compiled from")
mcp = MCPServer(
    name="land-query",
    instructions=(f"Parcel facts for {LQ.council.LABEL}{'' if LQ.national else ', New Zealand'}, compiled from {LQ.dataset_sources()}. "
                  "Every response lists, for each column, its kind (published, derived or modelled), meaning, sources, "
                  f"fit-for-parcel flag and licence status, and {PROVENANCE}. Coordinates are NZTM2000 metres. Start with "
                  "`about`, then `columns`. Derived and modelled values are estimates; say so when you pass them on. "
                  "Empty values mean unknown, never zero."),
)


def _call(f, *a, **k):
    """A tool's result, or {"error": ...}: a clear message for a bad request, a plain one for anything unexpected (the
    details stay in the server's log)."""
    try: return f(*a, **k)
    except QueryError as e: return {"error": str(e)}
    except (TypeError, ValueError, OverflowError, AttributeError) as e:
        import logging; logging.getLogger("land-query").warning("bad request: %r", e)
        return {"error": "the request could not be read: check each argument's type against the tool's description"}


@mcp.tool(description="What the data is, which build it comes from, the audience mode and licence notes.")
def about() -> dict:
    return _call(LQ.about)


@mcp.tool(description="Columns with their kind, meaning, sources, fit-for-parcel flag, licence status and whether they are served. Optional `contains` filters by name or meaning.")
def columns(contains: str | None = None) -> dict:
    return _call(LQ.describe_columns, contains)


@mcp.tool(description="Parcels by LINZ parcel id (`unit_id`: at most one) or by appellation (for example 'Lot 2 DP 58242'; matched "
                      "exactly, case and spaces included; one appellation can name many parcels, such as 'Crown Land', and the "
                      "first 20 are returned with the total), with every served column and its provenance. `columns` limits the columns returned.")
def parcel(unit_id: int | None = None, appellation: str | None = None, columns: list[str] | None = None) -> dict:
    return _call(LQ.parcel, unit_id, appellation, columns)


OPS = "=, !=, <, <=, >, >=, in, is_null, not_null, contains" + ("" if LQ.national else ", and has_class for overlay columns (value: a class name, or {class, min_pct})")


@mcp.tool(description=("Parcels in an area and/or matching filters. `bbox` is [xmin, ymin, xmax, ymax] in NZTM2000 metres (at most 20 km "
                       f"across). `where` is a list of {{column, op, value}}; ops: {OPS}. Up to 500 rows per call when `columns` names "
                       "20 or fewer columns, else 100 (the response's count says how many came); page with `offset`."))
def search(bbox: list[float] | None = None, where: list[dict] | None = None, columns: list[str] | None = None,
           limit: int = 100, offset: int = 0) -> dict:
    return _call(LQ.search, bbox, where, columns, limit, offset)


if not LQ.national:   # the national index has no precomputed queries
    @mcp.tool(description="A precomputed district query (Q1 to Q5: infill candidates, high floor levels, old poor sewers, ground change, heritage and trees) with its SQL, rows and provenance.")
    def query(id: str) -> dict:
        return _call(LQ.inverse_query, id)


class RateLimit:
    """ASGI middleware: at most `per_minute` requests a minute from one address (a token bucket) and one at a time (so
    one client cannot keep the database busy: each request holds it at most QUERY_SECONDS), and /health for the
    host's checks. Behind a proxy that appends the caller's address to X-Forwarded-For, LANDQ_TRUST_PROXY=1 takes the
    right-most entry, the one the proxy added; the others are the caller's own to invent (service review, 16 Nov)."""
    MAX_ADDRESSES = 100_000

    def __init__(self, app, per_minute=60, trust_proxy=False):
        import time, collections
        self.app, self.rate, self.trust, self.now = app, per_minute / 60.0, trust_proxy, time.monotonic
        self.cap, self.buckets, self.busy = float(per_minute), collections.OrderedDict(), set()

    def client(self, scope):
        if self.trust:
            for k, v in scope.get("headers", []):
                if k == b"x-forwarded-for": return v.decode("latin-1").split(",")[-1].strip()
        return (scope.get("client") or ("?",))[0]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http": return await self.app(scope, receive, send)
        if scope.get("path") == "/health": return await self._send(send, 200, b"ok")
        ip, t = self.client(scope), self.now()
        if ip in self.busy:
            return await self._send(send, 429, b"one request at a time from one address", [(b"retry-after", b"2")])
        tokens, last = self.buckets.pop(ip, (self.cap, t))
        tokens = min(self.cap, tokens + (t - last) * self.rate)
        self.buckets[ip] = (tokens - 1 if tokens >= 1 else tokens, t)      # most recent last
        while len(self.buckets) > self.MAX_ADDRESSES: self.buckets.popitem(last=False)   # the longest unseen go first
        if tokens < 1:
            return await self._send(send, 429, b"too many requests: at most %d a minute" % int(self.cap), [(b"retry-after", b"5")])
        self.busy.add(ip)
        try: return await self.app(scope, receive, send)
        finally: self.busy.discard(ip)

    @staticmethod
    async def _send(send, status, body, headers=()):
        await send(dict(type="http.response.start", status=status, headers=[(b"content-type", b"text/plain")] + list(headers)))
        await send(dict(type="http.response.body", body=body))


def http_app():
    """The service over HTTP (MCP streamable HTTP at /mcp, stateless JSON), for hosting (T-26). LANDQ_ALLOWED_HOSTS: the
    host names it answers to (comma-separated; checked against DNS rebinding); LANDQ_RATE: requests a minute per address."""
    from mcp.server.transport_security import TransportSecuritySettings
    hosts = [h.strip() for h in os.environ.get("LANDQ_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
    sec = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts + [h + ":*" for h in hosts],
                                    allowed_origins=[])
    app = mcp.streamable_http_app(stateless_http=True, json_response=True, transport_security=sec,
                                  max_request_body_size=64 * 1024, host="0.0.0.0")
    return RateLimit(app, int(os.environ.get("LANDQ_RATE", "60")), os.environ.get("LANDQ_TRUST_PROXY") == "1")


if __name__ == "__main__":
    if os.environ.get("LANDQ_TRANSPORT") == "http":
        import uvicorn
        # this machine only, unless told otherwise (the container sets LANDQ_HOST=0.0.0.0)
        uvicorn.run(http_app(), host=os.environ.get("LANDQ_HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")), log_level="warning")
    else:
        mcp.run("stdio")
