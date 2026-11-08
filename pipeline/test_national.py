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
    assert 20 <= r["road_frontage_m"] <= 22                            # the south side, plus up to 1 m up each end
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
    assert N.elevation_columns([parcel(box(50, 0, 150, 100))], Z, T, lid, acc, tr)[0]["ground_cells_pct"] == 50   # half past the grid
    assert t["elevation_from"] == "point" and t["ground_cells"] == 0 and t["ground_mean_m"] == round(float(Z[5, 4]), 1)
    Z2 = Z.copy(); Z2[:, :3] = np.nan                                   # no ground under the west parcel
    assert N.elevation_columns([parcel(big)], Z2, T, lid, acc, tr)[0]["ground_mean_m"] is None


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
