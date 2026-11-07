"""Tests for the query service (T-36). Run: python3 test_service.py"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import duckdb
import catalogue as cat
from landquery import LandQuery, QueryError

B1, B2 = "1765000_5465000_5000", "1770000_5470000_5000"


def fixture():
    d = tempfile.mkdtemp()
    rows = [
        (1, "Lot 1 DP 1", B1, '{"General Residential Zone": 100.0}', 5.2, 800.0, 1765100, 5465100, 1765150, 5465150),
        (2, "Lot 2 DP 1", B1, '{"Open Space Zone": 100.0}', 6.1, 1200.0, 1765200, 5465200, 1765260, 5465260),
        (3, "Lot 3 DP 2", B2, None, 12.0, 300.0, 1770100, 5470100, 1770120, 5470120),
    ]
    db = duckdb.connect()
    db.execute("""CREATE TABLE units (unit_id BIGINT, appellation VARCHAR, block_id VARCHAR, zones VARCHAR, ground_mean_m DOUBLE,
                  area_m2 DOUBLE, bbox_xmin DOUBLE, bbox_ymin DOUBLE, bbox_xmax DOUBLE, bbox_ymax DOUBLE)""")
    db.executemany("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    db.execute(f"COPY units TO '{os.path.join(d, 'units.parquet')}' (FORMAT PARQUET)")
    prov = {k: dict(url=f"https://example/{k}", by_block={B1: dict(sha256=k + "1", fetched="t1"), B2: dict(sha256=k + "2", fetched="t2")})
            for k in ("parcels", "dem_2025", "zones")}
    json.dump(prov, open(os.path.join(d, "provenance.json"), "w"))
    open(os.path.join(d, "RUN.txt"), "w").write("Run 1 from commit abc")
    json.dump(dict(queries=[dict(id="Q1", name="n", question="q", sql="s", count=1, provenance={}, rows=[dict(unit_id=1, zones="{}", sources={})]),
                            dict(id="Q4", name="n", question="q", sql="s", count=1, provenance={}, rows=[dict(unit_id=3, area_m2=300.0, sources={})])]),
              open(os.path.join(d, "inverse_queries.json"), "w"))
    return d


def test_catalogue_reads_licence_and_fit_from_sources_md():
    assert cat.SOURCES["zones"]["licence_cleared"] is False            # portal-wide statement only
    assert cat.SOURCES["dem_2025"]["licence_cleared"] is True
    assert cat.SOURCES["gw_liquefaction"]["fit"] == "not fit for parcel use"
    m = cat.column_meta("ww_head_ground_min_minus_invert_m")
    assert m["kind"] == "derived" and set(m["sources"]) == {"parcels", "ww_node", "dem_2025"}


def test_every_published_column_is_catalogued():
    p = os.environ.get("LANDQ_RESULTS")
    if not p: return  # needs the published results; the server also refuses to start if any column is missing
    cols = [r[0] for r in duckdb.connect().execute("DESCRIBE SELECT * FROM read_parquet(?)", [os.path.join(p, "units.parquet")]).fetchall()]
    assert [c for c in cols if cat.column_meta(c) is None] == []


def test_public_mode_withholds_portal_statement_columns_and_refuses_filters_on_them():
    lq = LandQuery(fixture(), "public")
    assert "zones" in lq.withheld and "ground_mean_m" in lq.columns
    r = lq.parcel(unit_id=1)
    assert "zones" not in r["rows"][0]["values"] and r["rows"][0]["values"]["ground_mean_m"] == 5.2
    for bad in (lambda: lq.search(where=[dict(column="zones", op="has_class", value="Open Space Zone")]),
                lambda: lq.search(columns=["zones"])):
        try: bad(); assert False, "should refuse"
        except QueryError as e: assert "T-35" in str(e)
    assert lq.inverse_query("Q1")["withheld"] is True and lq.inverse_query("Q4")["count"] == 1


def test_internal_mode_filters_overlay_classes_and_returns_provenance_per_block():
    lq = LandQuery(fixture(), "internal")
    r = lq.search(where=[dict(column="zones", op="has_class", value={"class": "General Residential Zone", "min_pct": 90})])
    assert [x["unit_id"] for x in r["rows"]] == [1] and r["rows"][0]["values"]["zones"] == {"General Residential Zone": 100.0}
    assert r["columns"]["ground_mean_m"]["kind"] == "derived"
    assert r["sources"]["dem_2025"]["by_block"] == {B1: dict(sha256="dem_20251", fetched="t1")}
    assert r["sources"]["dem_2025"]["licence_status"] == "dataset licence"


def test_area_and_value_filters():
    lq = LandQuery(fixture(), "internal")
    assert [x["unit_id"] for x in lq.search(bbox=[1765000, 5465000, 1766000, 5466000])["rows"]] == [1, 2]
    assert [x["unit_id"] for x in lq.search(where=[dict(column="area_m2", op=">=", value=800)])["rows"]] == [1, 2]
    assert lq.search(where=[dict(column="appellation", op="contains", value="DP 2")])["total"] == 1
    assert lq.search(limit=10_000)["count"] == 3


def test_injection_attempts_are_rejected():
    lq = LandQuery(fixture(), "internal")
    for cond in (dict(column='unit_id"; DROP TABLE units; --', op="=", value=1),
                 dict(column="zones", op="has_class", value='x"); DROP TABLE units; --'),
                 dict(column="unit_id", op="OR 1=1 --", value=1)):
        try: lq.search(where=[cond]); assert False, cond
        except QueryError: pass
    assert lq.search(where=[dict(column="appellation", op="=", value="x' OR '1'='1")])["total"] == 0  # values are parameters


def test_mcp_server_answers_over_stdio():
    import asyncio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    d = fixture()
    params = StdioServerParameters(command=sys.executable, args=[os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")],
                                   env=dict(os.environ, LANDQ_RESULTS=d, LANDQ_AUDIENCE="public"))

    async def run():
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                names = {t.name for t in (await s.list_tools()).tools}
                assert names >= {"about", "columns", "parcel", "search", "query"}, names
                res = await s.call_tool("parcel", {"unit_id": 2})
                body = json.loads(res.content[0].text)
                assert body["rows"][0]["appellation"] == "Lot 2 DP 1" and "zones" in body["withheld"]
    asyncio.run(run())


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
