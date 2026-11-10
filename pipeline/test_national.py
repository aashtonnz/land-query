"""Tests for the national index (T-100) on small made-up parcels; no network. Run: python3 test_national.py"""
import os, sys
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box, Point, LineString
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import national_index as N


def parcel(g, **p):
    return (g, dict(dict(id=1, titles=None, parcel_intent="DCDB"), **p), g.representative_point())


def test_tiles_cover_bounds_and_a_point_on_an_edge_belongs_to_one_tile():
    ts = N.tiles_for((1750000, 5420000, 1790000, 5430000))
    assert len(ts) == 2 and all(t[2] - t[0] == N.TILE for t in ts)
    edge = Point(ts[0][2], 5425000)
    assert sum(N.in_tile(edge, t) for t in ts) == 1


def test_selection_drops_roads_water_seabed_and_parcels_whose_point_is_elsewhere():
    t = (0, 0, 100, 100)
    f = lambda g, intent, i: dict(geometry=g.__geo_interface__, properties=dict(id=i, parcel_intent=intent))
    feats = [f(box(10, 10, 20, 20), "DCDB", 1), f(box(10, 30, 20, 40), "Road", 2), f(box(10, 50, 20, 60), "Hydro", 3),
             f(box(10, 70, 20, 80), "Common Marine and Coastal Area (Sec 237A(1)(b) RM Act)", 4),
             f(box(90, 10, 150, 20), "Fee Simple Title", 5)]           # most of it, and its point, in the next tile
    assert [p["id"] for _, p, _ in N.select_parcels(feats, t)] == [1]
    assert N.select_parcels(feats, t, region=box(50, 50, 60, 60)) == []


def test_vector_columns_measure_buildings_addresses_frontage_titles_and_coast():
    g = box(0, 0, 20, 30)                                               # 600 m², road along its south side
    p = parcel(g, titles="T1, T2, T9")
    roads = [(box(-50, -20, 70, 0), {})]
    bld = [(box(2, 2, 12, 12), dict(capture_source_to=1610582400000)),   # 100 m², inside
           (box(15, 25, 25, 35), dict(capture_source_to=1700000000000))]  # 100 m², a quarter inside: not counted
    adr = [(Point(5, 5), dict(full_address="3 A St", address_number=3, territorial_authority="X District")),
           (Point(6, 6), dict(full_address="1 A St", address_number=1, territorial_authority="X District")),
           (Point(50, 50), dict(full_address="far", address_number=0))]
    titles = {"T1": dict(type="Freehold"), "T2": dict(type="Cross lease")}
    coast = [(LineString([(0, -500), (100, -500)]), {})]
    r = N.vector_columns([p], roads, titles, bld, adr, coast)[0]
    assert r["area_m2"] == 600 and r["width_m"] == 20 and r["perimeter_m"] == 100
    assert r["building_count"] == 1 and r["building_m2"] == 125 and r["largest_building_m2"] == 100
    assert r["building_cover_pct"] == round(100 * 125 / 600, 1) and r["buildings_captured_to"] == "2023-11-14"
    assert r["address_count"] == 2 and r["address"] == "1 A St" and r["territorial_authority"] == "X District"
    assert 20 <= r["road_frontage_m"] <= 22                            # no neighbours given: up to 1 m up each side counts
    assert r["title_count"] == 3 and r["title_types"] == "Cross lease, Freehold" and r["titles_not_found"] == 1
    assert r["coast_distance_m"] == 500 and r["coast_over_10km"] is False
    far = N.vector_columns([p], [], {}, [], [], [(LineString([(0, -20000), (1, -20000)]), {})])[0]
    assert far["coast_distance_m"] is None and far["coast_over_10km"] is True and far["road_frontage_m"] == 0


def test_elevation_columns_from_cells_and_for_a_parcel_too_small_for_a_cell():
    T = from_origin(0, 100, 10, 10)                                    # 10 x 10 cells of 10 m
    Z = np.tile(np.arange(10, dtype=np.float32), (10, 1)) * 10 * np.tan(np.radians(10))   # a 10° slope to the east
    Z[:, :3] = 2.0                                                      # flat low ground on the west
    lid = np.ones(Z.shape, bool); lid[:, 8:] = False
    acc = np.arange(100, dtype=np.float32).reshape(10, 10) * 100; tr = np.zeros(Z.shape, bool); tr[9, 9] = True
    acc[3, 5] = 50000                                                   # the largest upslope area is not the highest cell
    big, east, tiny = box(0, 0, 20, 100), box(50, 0, 100, 100), box(41, 41, 44, 44)
    rows = N.elevation_columns([parcel(big), parcel(east), parcel(tiny)], Z, T, lid, acc, tr)
    b, e, t = rows
    assert b["ground_mean_m"] == 2 and b["flat_pct"] == 100 and b["low_lying_pct"] == 100 and b["ground_cells"] == 20
    assert b["ground_cells_pct"] == 100 and b["elevation_from"] == "cells" and b["lidar_pct"] == 100
    assert abs(e["slope_mean_deg"] - 10) < 0.2 and e["steep_pct"] == 0 and e["lidar_pct"] == 60
    assert e["upslope_area_max_m2"] == 50000 and e["upslope_truncated"] is False and e["flat_pct"] == 0
    acc[3, 5] = 0
    assert N.elevation_columns([parcel(east)], Z, T, lid, acc, tr)[0]["upslope_truncated"] is True   # from cell (9, 9)
    assert N.elevation_columns([parcel(box(54, 0, 66, 10))], Z, T, lid, acc, tr)[0]["ground_cells_pct"] == 100   # 2 cells, 1.2 by area
    Z3 = Z.copy(); Z3[:, 8:] = np.nan
    assert N.elevation_columns([parcel(east)], Z3, T, lid, acc, tr)[0]["ground_cells_pct"] == 60   # of its own cells, 3 of 5 columns have ground
    assert t["elevation_from"] == "point" and t["ground_cells"] == 0 and t["ground_mean_m"] == round(float(Z[5, 4]), 1)
    Z2 = Z.copy(); Z2[:, :3] = np.nan                                   # no ground under the west parcel
    assert N.elevation_columns([parcel(big)], Z2, T, lid, acc, tr)[0]["ground_mean_m"] is None


def test_repeated_records_are_kept_once_and_counted():
    f = lambda k, v: dict(properties=dict(id=k, v=v))
    out, rep, diff = N.once_each([f(1, "a"), f(2, "b"), f(1, "a"), f(2, "c"), f(None, "x"), f(None, "y")], "id")
    assert [x["properties"]["v"] for x in out] == ["a", "b", "x", "y"] and rep == 2 and diff == 1


def test_report_block_holds_the_whole_parcel_and_refuses_huge_ones():
    import parcel_report as R
    g = box(1000.3, 2000.7, 1062.0, 2031.0)
    x, y, size = R.block_for(g)
    assert x <= 1000.3 and y <= 2000.7 and x + size >= 1062 and y + size >= 2031 and size % 10 == 0
    assert box(x, y, x + size, y + size).contains(g.representative_point())
    try: R.block_for(box(0, 0, 3500, 10)); raise AssertionError("accepted")
    except SystemExit: pass


def test_report_page_shows_missing_values_as_not_known_and_never_zero():
    import report_page as P
    rep = dict(parcel_id=7, address="1 Test Road, Town", geometry=box(0, 0, 20, 30).__geo_interface__, buildings_nearby=[],
               values=dict(area_m2=600.0, easements_n=None, building_m2=0, upslope_area_truncated=False, rep_x=1.0, rep_y=2.0),
               lidar_surveys=dict(dem=[], dsm=[]), sources={})
    h = P.page(rep)
    assert "<title>1 Test Road, Town</title>" in h and "not known" in h and "600" in h
    row = lambda label: h.split(f"<dt>{label}</dt>")[1].split("</dd>")[0]
    assert "not known" in row("Easements") and row("Under buildings").count("0") >= 1 and "No" in row("Could be larger")
    assert "No LiDAR survey covers this parcel" in h


def test_a_gap_in_a_lidar_sheet_is_no_data_not_a_height():
    """T-107: the read the report uses (lidar_catalogue.read_sheets) never returns a sheet's -9999 as a height, and the
    second sheet fills only where the first has no data."""
    import tempfile, rasterio
    from lidar_catalogue import read_sheets
    d = tempfile.mkdtemp(); paths = []
    for k, (lo, val) in enumerate([(0, 5.0), (10, 7.0)]):
        a = np.full((20, 20), -9999, np.float32); a[:, lo:lo + 10] = val
        p = os.path.join(d, f"s{k}.tif"); paths.append(p)
        with rasterio.open(p, "w", driver="GTiff", height=20, width=20, count=1, dtype="float32", crs="EPSG:2193",
                           transform=from_origin(0, 20, 1, 1), nodata=-9999) as f: f.write(a, 1)
    out = read_sheets(paths, (-5, 0, 25, 20))
    assert np.nanmin(out) == 5.0 and np.isnan(out[:, :5]).all() and np.isnan(out[:, 25:]).all()
    assert (out[:, 5:15] == 5.0).all() and (out[:, 15:25] == 7.0).all()


def test_a_real_low_height_is_kept():
    from lidar_catalogue import no_data_to_nan
    assert no_data_to_nan(np.array([-101.5, -9999.0], np.float32), None)[0] == np.float32(-101.5)   # Martha pit, Waihi


def test_surface_model_rule_empties_only_below_99_pct():
    import overlays as ov
    r = {c: 1.0 for c in ov.DSM_COLUMNS}; r["ground_mean_m"] = 5.0
    assert ov.empty_without_dsm(dict(r), 99.5) == r
    e = ov.empty_without_dsm(dict(r), 98.0)
    assert all(e[c] is None for c in ov.DSM_COLUMNS) and e["ground_mean_m"] == 5.0


def test_frontage_counts_a_road_set_slightly_off_the_line_but_not_the_side_boundaries():
    g = box(0, 0, 20, 30)
    left, right = box(-20, 0, 0, 30), box(20, 0, 40, 30)
    road = box(-50, -20, 70, -0.25)                                     # 0.25 m off the lot line, as LINZ roads often are
    r = N.vector_columns([parcel(g, id=1)], [(road, {})], {}, [], [], [], neighbours=[(g, dict(id=1)), (left, dict(id=2)), (right, dict(id=3))])[0]
    assert 19.6 <= r["road_frontage_m"] <= 20.0, r["road_frontage_m"]


def run_tile(monkey_layers, Z=None, region=None, core=None, names=()):
    """index_tile on made-up LINZ data (no network): monkey_layers maps a layer name (or 'roads') to [(geometry, props)]."""
    monkey_layers.setdefault("land", [(box(-1e6, -1e6, 1e6, 1e6), dict(id=0))])
    from shapely.geometry import box as _box
    feat = lambda g, p: dict(geometry=g.__geo_interface__, properties=p)
    def fake_fetch(layer, bbox, cache, where="1=1"):
        key = "roads" if "Road" in where else layer
        return [feat(g, p) for g, p in monkey_layers.get(key, [])], dict(features=0)
    T = from_origin(-200, 1200, 10, 10)
    Zg = np.full((140, 140), 5.0, np.float32) if Z is None else Z
    keep = (N.fetch, N.elevation_grid, N.REGION_CORE, N.REGION_NAMES)
    N.fetch = fake_fetch
    N.elevation_grid = lambda tile: (Zg, T, [], np.ones(Zg.shape, bool), np.ones(Zg.shape, np.float32) * 100, np.zeros(Zg.shape, bool))
    N.REGION_CORE, N.REGION_NAMES = core, set(names)
    try: rows, prov = N.index_tile((0, 0, 1000, 1000), "/nonexistent", region)
    finally: N.fetch, N.elevation_grid, N.REGION_CORE, N.REGION_NAMES = keep
    return {r["parcel_id"]: r for r in rows}


def test_water_is_measured_not_guessed_from_names_or_titles():
    """T-113: a lake bed reads as water; reclaimed land named as a harbour bed, untitled and unaddressed, stays land."""
    lot = box(100, 100, 140, 140); lakebed = box(300, 300, 500, 500); reclaimed = box(600, 100, 700, 200)
    P = lambda i, app, intent="DCDB", titles=None: dict(id=i, appellation=app, parcel_intent=intent, titles=titles)
    rows = run_tile({"parcels": [(lot, P(1, "Lot 1 DP 1", "Fee Simple Title", "T1")), (lakebed, P(2, "Section 1 SO 518213", "Legalisation", "T2")),
                                 (reclaimed, P(3, "Part Bed Port Nicholson SO 31787"))],
                     "lakes": [(box(280, 280, 520, 520), dict(t50_fid=1))],
                     "land": [(box(-1000, -1000, 2000, 2000), dict(id=1))],
                     "titles": [(lot, dict(title_no="T1", status="LIVE", type="Freehold")), (lakebed, dict(title_no="T2", status="PRTC", type="Freehold"))]})
    assert rows[2]["title_types"] == "Freehold" and rows[2]["titles_not_found"] == 0   # partly cancelled is current, through index_tile
    assert set(rows) == {1, 2, 3}                                       # nothing dropped by its name or paperwork
    assert rows[2]["water_pct"] == 100 and rows[1]["water_pct"] == 0 and rows[3]["water_pct"] == 0


def test_water_is_the_area_of_sea_lakes_and_rivers_together_never_from_the_grid():
    """T-115: sea is outside the land outline; a part both lake and sea counts once; no elevation data is not water."""
    Z = np.full((140, 140), np.nan, np.float32)                           # no elevation data at all
    land = box(-500, -500, 600, 1500)                                       # sea east of x = 600
    P = lambda i: dict(id=i, parcel_intent="DCDB")
    rows = run_tile({"parcels": [(box(100, 100, 200, 200), P(1)), (box(620, 100, 720, 200), P(2)),   # 20 m offshore
                                 (box(540, 300, 640, 400), P(3)),           # 40% sea
                                 (box(400, 500, 700, 600), P(4)),           # under a lake (450-650) that runs over the sea edge (600)
                                 (box(100, 700, 200, 800), P(5))],          # half under a lake, half under a river
                     "land": [(land, dict(id=1))],
                     "lakes": [(box(450, 450, 650, 650), dict(t50_fid=1)), (box(100, 700, 150, 800), dict(t50_fid=2))],
                     "rivers": [(box(150, 700, 200, 800), dict())]}, Z=Z)
    assert rows[1]["water_pct"] == 0 and rows[3]["water_pct"] == 40
    assert rows[2]["water_pct"] is None                                     # wholly outside the outline: unknown (T-123)
    assert rows[4]["water_pct"] == 83.3                                     # 450-700 once: 250 of 300 (counted twice it would be 100)
    assert rows[5]["water_pct"] == 100 and rows[1]["ground_mean_m"] is None


def test_no_land_outline_means_water_unknown_not_sea():
    """T-117: where LINZ's land outline has nothing (the Chatham islets), water is empty, and the run does not stop."""
    rows = run_tile({"parcels": [(box(100, 100, 200, 200), dict(id=1, parcel_intent="DCDB"))], "land": []})
    assert rows[1]["water_pct"] is None


def test_the_cache_key_includes_the_fetch_detail_and_the_window():
    """T-117: the same layer and window at another detail, or another window, is a new download, never a cached one."""
    import tempfile, arcgis
    calls = []
    keep = (arcgis.query_all, dict(N.FETCH_OPTS))
    arcgis.query_all = lambda url, q, workers=1: calls.append(q.get("maxAllowableOffset")) or []
    try:
        d = tempfile.mkdtemp()
        N.fetch("land", (0, 0, 10, 10), d); N.fetch("land", (0, 0, 10, 10), d)          # cached the second time
        N.FETCH_OPTS["land"] = dict(workers=1, maxAllowableOffset=50); N.fetch("land", (0, 0, 10, 10), d)
        N.fetch("land", (0, 0, 20, 10), d)
    finally: arcgis.query_all, N.FETCH_OPTS = keep[0], keep[1]
    assert calls == [5, 50, 50], calls


def test_a_parcel_half_or_more_in_unconfirmed_sea_is_unknown_whatever_the_heights():
    """T-123, T-125: LINZ's outline leaves out rocks and islets, right by the shore as well as far out, and the elevation
    grid holds a flat sea surface there, so neither can tell a rock from the sea. Sea that no lake or river covers, on
    half the parcel or more, means unknown; under half is measured."""
    land = box(-500, -500, 300, 1500)                                       # sea east of x = 300
    Z = np.full((140, 140), -0.6, np.float32)                               # the sea surface, low everywhere
    P = lambda i: dict(id=i, parcel_intent="DCDB")
    rows = run_tile({"parcels": [(box(310, 110, 340, 140), P(1)),            # a rock 10 m off the outline, low "heights"
                                 (box(250, 200, 350, 300), P(2)),            # exactly half outside
                                 (box(247, 320, 347, 420), P(3)),            # 47% outside: measured
                                 (box(600, 600, 700, 700), P(4)),            # wholly outside, a river mouth over 55%
                                 (box(600, 800, 700, 900), P(5)),            # wholly outside, a river over 45%
                                 (box(240, 700, 400, 780), P(6)),           # 62.5% outside, a river over the sea part of 25 of it
                                 (box(240, 450, 300, 510), P(7))],           # wholly inside
                     "rivers": [(box(600, 600, 655, 700), dict()), (box(600, 800, 645, 900), dict()), (box(375, 700, 400, 780), dict())],
                     "land": [(land, dict(id=1))]}, Z=Z)
    assert rows[1]["water_pct"] is None and rows[2]["water_pct"] is None and rows[5]["water_pct"] is None
    assert rows[3]["water_pct"] == 47 and rows[4]["water_pct"] == 100 and rows[6]["water_pct"] == 62.5 and rows[7]["water_pct"] == 0


def test_region_margin_keeps_only_parcels_whose_district_is_the_regions():
    core = box(0, 0, 500, 1000); grown = box(0, 0, 1000, 1000)
    rows = run_tile({"parcels": [(box(100, 100, 150, 150), dict(id=1, parcel_intent="DCDB")),
                                 (box(600, 100, 650, 150), dict(id=2, parcel_intent="DCDB")),     # margin, nearest address elsewhere
                                 (box(600, 800, 650, 850), dict(id=3, parcel_intent="DCDB"))],    # margin, nearest address in the region
                     "addresses": [(Point(640, 160), dict(full_address="1 Beach Rd", address_number=1, territorial_authority="Horowhenua District")),
                                   (Point(640, 860), dict(full_address="2 Shore Rd", address_number=2, territorial_authority="Kāpiti Coast District"))]},
                    region=grown, core=core, names=["kapiti coast district"])
    assert set(rows) == {1, 3}
    # an island in the margin with no address within 1 km stays (Kapiti Island; T-115)
    island = run_tile({"parcels": [(box(900, 450, 950, 500), dict(id=4, parcel_intent="DCDB"))],
                       "addresses": [(Point(-900, 450), dict(full_address="9 Far Rd", address_number=9, territorial_authority="Horowhenua District"))]},
                      region=grown, core=core, names=["kapiti coast district"])
    assert set(island) == {4}


def test_frontage_counts_across_a_thin_strip_to_the_road():
    g = box(0, 0, 20, 30)
    strip = box(0, -0.2, 20, 0)                                          # a 0.2 m reserve strip between the lot and the road
    road = box(-50, -20, 70, -0.2)
    r = N.vector_columns([parcel(g, id=1)], [(road, {})], {}, [], [], [], neighbours=[(strip, dict(id=9)), (box(-20, 0, 0, 30), dict(id=2)), (box(20, 0, 40, 30), dict(id=3))])[0]
    assert 19.6 <= r["road_frontage_m"] <= 22.0, r["road_frontage_m"]   # never 0 across the strip
    assert 19.6 <= r["road_frontage_via_strip_m"] <= 22.0                # and reported as reached across a strip (T-113)
    r2 = N.vector_columns([parcel(g, id=1)], [(box(-50, -20, 70, -0.25), {})], {}, [], [], [], neighbours=[(box(-20, 0, 0, 30), dict(id=2))])[0]
    assert r2["road_frontage_via_strip_m"] == 0


def test_no_vesting_text_and_current_titles_in_every_fetch():
    import inspect
    assert "statutory_actions" not in N.LAYERS["parcels"][1]
    assert "PRTC" in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch_parcels.py")).read()
    assert N.plain("Kāpiti Coast District") == "kapiti coast district"


def test_surface_model_columns_cover_what_the_dsm_measures():
    import overlays as ov
    for c in ("open_ground_clear_pct", "winter_sun_hours_open_mean", "sky_view_pct", "roof_pitch_p50_deg", "canopy_gt3m_open_pct"):
        assert c in ov.DSM_COLUMNS
    assert "ground_mean_m" not in ov.DSM_COLUMNS and "slope_p50_deg" not in ov.DSM_COLUMNS


def test_partly_cancelled_titles_count_as_current_and_beds_are_not_land():
    f = lambda no, st: dict(properties=dict(title_no=no, status=st, type="Freehold"))
    assert set(N.current_titles([f("A", "LIVE"), f("B", "PRTC"), f("C", "CANC")])) == {"A", "B"}


def test_national_districts_come_from_linz_localities():
    """T-102: with no district polygons given, a parcel's district is that of the LINZ locality holding its point."""
    rows = run_tile({"parcels": [(box(100, 100, 200, 200), dict(id=1, parcel_intent="DCDB")), (box(600, 100, 700, 200), dict(id=2, parcel_intent="DCDB"))],
                     "localities": [(box(0, 0, 500, 1000), dict(id=1, territorial_authority="Kāpiti Coast District")),
                                    (box(500, 0, 1000, 1000), dict(id=2, territorial_authority="Porirua City"))]})
    assert rows[1]["territorial_authority"] == "Kāpiti Coast District" and rows[2]["territorial_authority"] == "Porirua City"


def test_the_national_merge_writes_nothing_unless_every_share_and_tile_is_there_once():
    import tempfile, json, pandas as pd, national_merge as M
    d = tempfile.mkdtemp(); tiles = [(0, 0, 1, 1), (1, 0, 2, 1)]
    def share(k, tile, ids, commit="c"):
        os.makedirs(f"{d}/s/{k}", exist_ok=True)
        pd.DataFrame(dict(parcel_id=ids, water_pct=[1.0] * len(ids), territorial_authority=["X"] * len(ids))).to_parquet(f"{d}/s/{k}/index.parquet")
        json.dump(dict(tiles=[dict(tile=list(tile))], built="2026", commit=commit, region=dict(districts="L")), open(f"{d}/s/{k}/provenance.json", "w"))
        json.dump(dict(seconds=1), open(f"{d}/s/{k}/run.json", "w"))
    share(0, tiles[0], [1, 2])
    for bad in ("missing", "duplicate", "commit", "tile"):
        share(1, tiles[1], {"missing": [3], "duplicate": [2, 3], "commit": [3], "tile": [3]}[bad],
              commit="other" if bad == "commit" else "c")
        if bad == "tile": json.dump(dict(tiles=[dict(tile=list(tiles[0]))], built="2026", commit="c", region={}), open(f"{d}/s/1/provenance.json", "w"))
        try: M.merge(f"{d}/s", f"{d}/out", 3 if bad == "missing" else 2, tiles); assert False, bad
        except SystemExit: assert not os.path.exists(f"{d}/out"), bad
    share(1, tiles[1], [3]); M.merge(f"{d}/s", f"{d}/out", 2, tiles)
    assert len(pd.read_parquet(f"{d}/out/index.parquet")) == 3


def test_published_results_hold_no_title_references_or_types():
    """T-106: public_strip drops titles and title_types from tables and from query rows, and keeps the count."""
    import tempfile, json, pandas as pd, public_strip
    d = tempfile.mkdtemp()
    pd.DataFrame(dict(unit_id=[1], titles=["WN1/1"], title_types=["Life Estate"], title_count=[1])).to_parquet(f"{d}/units.parquet")
    json.dump(dict(provenance=dict(titles=dict(url="u")), rows=[dict(unit_id=1, title_types="Life Estate", area_m2=5)]), open(f"{d}/q.json", "w"))
    public_strip.strip(d)
    assert list(pd.read_parquet(f"{d}/units.parquet").columns) == ["unit_id", "title_count"]
    assert "Life Estate" not in open(f"{d}/q.json").read() and json.load(open(f"{d}/q.json"))["provenance"]["titles"] == dict(url="u")
    rep = dict(values=dict(titles="WN1/1", title_types="Life Estate", title_count=1), provenance=dict(titles=dict(url="u")))
    assert public_strip.strip_json(rep) == dict(values=dict(title_count=1), provenance=dict(titles=dict(url="u")))   # the parcel report


def test_no_stage_grows_faster_than_the_data():
    """T-102: each stage timed on made-up suburbs of about 1,000, 2,000 and 4,000 parcels on a detailed coast; the growth
    (slope of log time against log parcels) must stay under scaling.MAX_SLOPE. The per-parcel water share that took hours
    on Auckland's coast measured 1.4 to 1.6 here; the fixed one about 1.0."""
    import scaling
    for stage, (k, t, ns) in scaling.slopes(1000, repeats=2).items():
        assert k < scaling.MAX_SLOPE, f"{stage} grows as parcels^{k:.2f} ({ns}): too steep for the densest tiles"


def test_bulk_reads_geopackage_geometry_and_only_the_fields_named():
    """T-102: a GeoPackage geometry blob (header, envelope, WKB) gives the shape back; owner fields are never read."""
    import sqlite3, struct, tempfile, shapely, bulk
    g = shapely.Polygon([(0, 0), (10, 0), (10, 10)])
    blob = b"GP" + bytes([0, 1 << 1 | 1]) + struct.pack("<i", 2193) + struct.pack("<4d", 0, 10, 0, 10) + shapely.to_wkb(g)
    assert shapely.from_wkb(bulk.gpkg_wkb(blob)).equals(g)
    d = tempfile.mkdtemp(); con = sqlite3.connect(f"{d}/t.gpkg")
    con.execute("CREATE TABLE gpkg_geometry_columns (table_name, column_name)"); con.execute("INSERT INTO gpkg_geometry_columns VALUES ('t', 'shape')")
    con.execute("CREATE TABLE t (title_no, status, type, number_owners, estate_description, shape)")
    con.execute("INSERT INTO t VALUES ('WN1/1', 'LIVE', 'Freehold', 2, 'Fee Simple, 1/2 share', ?)", (blob,)); con.commit()
    cols, wkbs = bulk.read_gpkg(f"{d}/t.gpkg", bulk.LDS_LAYERS["titles"][1])
    assert set(cols) == {"title_no", "status", "type"} and cols["title_no"] == ["WN1/1"] and len(wkbs) == 1
    try: bulk.read_gpkg(f"{d}/t.gpkg", dict(x="missing_field")); assert False
    except RuntimeError: pass


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
