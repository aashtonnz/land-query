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


def test_titled_or_addressed_land_named_as_a_bed_is_kept():
    import inspect
    src = inspect.getsource(N.index_tile)
    assert 'not r.get("address_count")' in src and "is_bed(" in src and 'not (p.get("titles")' in src


def test_frontage_counts_across_a_thin_strip_to_the_road():
    g = box(0, 0, 20, 30)
    strip = box(0, -0.2, 20, 0)                                          # a 0.2 m reserve strip between the lot and the road
    road = box(-50, -20, 70, -0.2)
    r = N.vector_columns([parcel(g, id=1)], [(road, {})], {}, [], [], [], neighbours=[(strip, dict(id=9)), (box(-20, 0, 0, 30), dict(id=2)), (box(20, 0, 40, 30), dict(id=3))])[0]
    assert 19.6 <= r["road_frontage_m"] <= 22.0, r["road_frontage_m"]   # never 0 across the strip


def test_no_vesting_text_and_current_titles_in_every_fetch():
    import inspect
    assert "statutory_actions" not in N.LAYERS["parcels"][1]
    assert "current_titles(tf)" in inspect.getsource(N.index_tile)
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
    assert N.is_bed("Part Bed Porirua Harbour") and N.is_bed("River Bed") and not N.is_bed("Old River Bed Block II")


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
