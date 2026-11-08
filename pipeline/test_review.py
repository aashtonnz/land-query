"""Regression checks for fixes from the fresh-eyes review (T-39). Run: python3 test_review.py"""
import os
import tile_env as te


def test_copyright_naming_a_person_is_withheld():
    staff = "created and uploaded by JamesC x521 23 January 2012; source data provided by MattA x840 someone@example.govt.nz"
    assert "@" not in te.scrub_copyright(staff) and "MattA" not in te.scrub_copyright(staff)
    assert te.scrub_copyright("Kapiti Coast District Council") == "Kapiti Coast District Council"
    assert te.scrub_copyright(None) == ""


def test_overlapping_features_of_one_class_are_not_double_counted():
    from shapely.geometry import box
    from overlays import class_shares
    parcel = box(0, 0, 10, 10)
    feats = [(box(-5, -5, 15, 15), {"ePlan_Zone": "High Density Residential Zone"}),
             (box(-1, -1, 11, 11), {"ePlan_Zone": "High Density Residential Zone", "PDP_ZONE": "Residential"})]
    assert class_shares("zones", parcel, feats) == {"High Density Residential Zone": 100.0}


def test_zone_label_is_the_operative_zone_not_the_legacy_name():
    from overlays import class_label
    assert class_label("zones", {"PDP_ZONE": "Beach Residential", "ePlan_Zone": "General Residential Zone"}) == "General Residential Zone"


def test_layer_label_is_its_class_never_the_column_name():
    from overlays import class_label
    assert class_label("tsunami_zones", {"Evac_Zone": "Shore Exclusion Zone"}) == "Shore Exclusion Zone"
    for layer in ("ovl_coastal_env", "wind_stainless", "wind_very_high", "earthworks", "flood_ponding", "ovl_noise_corridor"):
        assert class_label(layer, {}) != layer


def test_query_rows_carry_their_own_blocks_sha256_and_fetch_time():
    from provenance import merge_sources, row_sources, source_summary
    blk = lambda x, sha, t: dict(block=[x, 0, x + 5000, 5000], sources=dict(
        zones=dict(url="u", licence="CC BY 4.0", ok=True, features=3, sha256=sha, fetched=t),
        dem_2021=dict(ok=False, no_coverage=True)))
    P = merge_sources([blk(0, "aa", "2026-11-06T01:00:00+00:00"), blk(5000, "bb", "2026-11-06T02:00:00+00:00")])
    assert row_sources(P, ["zones", "dem_2021"], "5000_0_5000") == {"zones": dict(sha256="bb", fetched="2026-11-06T02:00:00+00:00")}
    s = source_summary(P["zones"])
    assert s["fetched_first"] < s["fetched_last"] and "features" not in s  # no sum over overlapping windows
    assert P["dem_2021"]["failed_blocks"] == 0  # outside the survey is not a failure
    lidar = dict(collection="https://nz-elevation.s3/x/collection.json", ok=True, sha256="cc", fetched="t", licence="CC BY 4.0")
    assert source_summary(lidar)["url"]  # a single block: LiDAR records its STAC collection, not a url


def test_lidar_sheet_search_box_covers_all_four_corners():
    from pyproj import Transformer
    tr = Transformer.from_crs(2193, 4326, always_xy=True)
    win = (1764765, 5469237, 1775355, 5480800)  # block 1765000_5470000; a sheet was missed on its east side
    w, s, e, n = te.ll_envelope(win)
    for x, y in ((win[0], win[1]), (win[2], win[1]), (win[0], win[3]), (win[2], win[3])):
        lon, lat = tr.transform(x, y)
        assert w <= lon <= e and s <= lat <= n
    assert te.lidar_bbox("/nonexistent")[0] == te.BLOCK[0] - te.LIDAR_CONTEXT_M


def test_every_cell_drains_to_an_outlet_across_flats_and_pits():
    import numpy as np
    from rasterio.transform import from_origin
    from flow import flow_routing
    rows, cols = 60, 41
    x = np.abs(np.arange(cols) - 20)[None, :] * 0.5            # valley walls
    dem = (np.arange(rows, 0, -1)[:, None] * 0.1 + x).astype(np.float32)
    dem[20:30, :] = np.minimum(dem[20:30, :], 4.0)              # a flat valley floor across the middle
    dem[40:43, 19:22] = 0.5                                     # a pit on the valley floor
    inflow = np.zeros(dem.shape, bool); inflow[0, :] = True     # only the north edge brings flow from outside
    acc, trunc, step = flow_routing(dem, from_origin(0, rows, 1, 1), inflow=inflow)
    floor_out = float(acc[-1, 20])                              # the valley floor at the south edge
    assert floor_out > 600, floor_out                           # the flat and the pit pass flow on, not swallow it
    assert trunc[-1, 20] and not trunc[-1, 0]
    assert abs(float(np.nanmax(step)) - 2 ** 0.5) < 1e-6


def test_real_valley_floor_has_no_dead_ends():
    """LINZ DEM crop where pysheds left a valley cell with no flow direction, cutting off the Ōtaki River."""
    import os
    import numpy as np
    from affine import Affine
    import flow
    f = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "otaki_valley_10m.npz"))
    z, T = f["z"], Affine(*f["transform"])
    ok = np.isfinite(z)
    out = np.zeros(z.shape)
    rec, dirn = flow._receivers(flow._fill(z.astype(np.float32), ok, out), ok, out)
    assert (dirn[1:-1, 1:-1] >= 0).all()                          # every interior cell drains somewhere
    acc = flow.flow_routing(z, T)[0]
    assert float(np.nanmax(acc)) / 100 > 6000, np.nanmax(acc)     # pysheds: 4,636 cells reach the outlet


def test_wind_relative_height_counts_the_sea_at_sea_level():
    import numpy as np
    from district_flow import mean_ground
    z = np.full((101, 101), np.nan, np.float32); z[:, 50:] = 20.0     # land at 20 m east of the beach, sea to the west
    m = mean_ground(z, 10.0)
    assert abs(float(m[50, 50]) - 10.0) < 0.5, m[50, 50]              # half sea at 0 m, half land at 20 m


def test_no_winter_sun_on_the_ground_under_a_tree():
    import numpy as np
    import measures as M
    dem = np.zeros((60, 60), np.float32); dsm = dem.copy(); dsm[25:35, 25:35] = 10.0   # a 10 m tree on flat ground
    lit = M.sunlit(dsm, 0.0, 89.0)                                                   # sun nearly overhead
    ground = lit & M.ground_clear(dsm, dem)
    assert lit[30, 30] and not ground[30, 30]   # the canopy top is lit, the ground beneath it is not
    assert ground[5, 5]


def test_viewpoint_is_never_under_trees():
    import numpy as np
    import measures as M
    og = np.zeros((40, 40), bool); og[2:38, 2:38] = True
    clear = np.ones_like(og); clear[10:30, 10:30] = False                            # trees in the middle of the section
    r, c = M.viewpoint(og, clear)
    assert clear[r, c] and og[r, c]
    assert M.viewpoint(og, np.zeros_like(og)) is None


def test_no_platform_where_15m_square_does_not_fit():
    import numpy as np
    import measures as M
    sliver = np.zeros((40, 40), bool); sliver[5:35, 10:22] = True                    # 12 m wide: too narrow
    assert not M.platform_centres(sliver).any()
    lot = np.zeros((40, 40), bool); lot[5:25, 5:25] = True                           # 20 m × 20 m
    assert M.platform_centres(lot).sum() == 36                                       # 6 × 6 centres


def test_paging_continues_when_the_server_returns_fewer_than_asked_and_flags_it_in_properties():
    from arcgis import page_through
    data = list(range(1234))
    def server(offset, n):  # a server whose own limit is 500, flagging truncation where f=geojson puts it
        fs = data[offset:offset + min(n, 500)]
        return {"features": fs, "properties": {"exceededTransferLimit": offset + len(fs) < len(data)}}
    assert len(page_through(server, 1000)) == 1234


def test_heritage_point_just_outside_the_parcel_is_not_counted():
    from shapely.geometry import Point, box
    from overlays import points_on
    parcel = box(0, 0, 20, 20)
    pts = [(Point(20.5, 10), {"TREE_ID": "T1"}), (Point(20, 10), {"TREE_ID": "T2", "SIGNIFICANCE": ""}),
           (Point(5, 5), {"TREE_ID": "T3", "SIGNIFICANCE": "Group A"})]
    assert points_on(parcel, pts, "TREE_ID") == [dict(id="T2", significance=None), dict(id="T3", significance="Group A")]


def test_nearest_pipe_does_not_depend_on_source_order():
    from shapely.geometry import LineString, box
    from overlays import nearest_item, worst_grade
    parcel = box(0, 0, 20, 20)
    a = (LineString([(10, -5), (10, 10)]), {"asset_id": "KWWP001431", "condition_grade": 4})
    b = (LineString([(10, 10), (10, 30)]), {"asset_id": "KWWP001430", "condition_grade": 2})
    for order in ([a, b], [b, a]):
        d, p, tied = nearest_item(order, [0, 1], parcel, prefer=worst_grade)
        assert p["asset_id"] == "KWWP001431" and tied == ["KWWP001430", "KWWP001431"]


def test_tied_manholes_inside_a_parcel_choose_the_deepest_invert_and_respect_the_distance_limit():
    from shapely.geometry import Point, box
    from overlays import nearest_item, deepest_invert
    parcel = box(0, 0, 20, 20)
    mh = [(Point(5, 5), {"asset_id": "KWWN003040", "invert_level_nzvd2016": 2.40}),
          (Point(15, 15), {"asset_id": "KWWN003039", "invert_level_nzvd2016": 2.71}),
          (Point(15, 5), {"asset_id": "KWWN003041", "invert_level_nzvd2016": None})]
    d, p, tied = nearest_item(mh, [0, 1, 2], parcel, prefer=deepest_invert)
    assert p["asset_id"] == "KWWN003040" and len(tied) == 3
    far = [(Point(200, 10), {"asset_id": "X"})]
    assert nearest_item(far, [0], parcel, maxd=150) == (None, None, [])   # 180 m away: beyond the 150 m limit


def test_beach_cells_drain_into_the_sea_not_along_the_beach():
    """Second review finding 1: a coast sloping gently south made every beach cell drain sideways, so one collected
    the whole coast. Each row should reach the sea at its own beach cell."""
    import numpy as np
    from rasterio.transform import from_origin
    from flow import flow_routing
    rows, cols = 50, 10
    z = (np.arange(cols)[None, :] * 1.0 + np.arange(rows, 0, -1)[:, None] * 0.05).astype(np.float32)
    z[:, 0] = np.nan                                                    # the sea, west of the beach
    acc = flow_routing(z, from_origin(0, rows, 1, 1))[0]
    assert float(np.nanmax(acc)) <= 3 * (cols - 1), np.nanmax(acc)      # pysheds-era code: 450 cells at one beach cell


def test_cell_beside_a_higher_survey_gap_is_not_an_outlet():
    """A pit next to higher unsurveyed ground must fill and overflow downhill, not drain into the gap (T-59 finding 7)."""
    import numpy as np
    import flow
    z = np.tile(np.arange(20, 0, -1, dtype=np.float32)[:, None], (1, 5)).copy()
    z[0:3, :] = np.nan                                   # a survey gap at the top
    z[3, 2] = 5.0                                        # a pit right beside it, far below its neighbours
    outside = np.full(z.shape, np.nan); outside[0:3, :] = 30.0
    ok = np.isfinite(z)
    zf = flow._fill(z, ok, np.where(np.isfinite(outside), outside, flow.SEA_M))
    rec, dirn = flow._receivers(zf, ok, np.where(np.isfinite(outside), outside, flow.SEA_M))
    assert rec[3 * 5 + 2] >= 0                           # it drains to a land neighbour, not out through the gap
    assert zf[3, 2] > 16                                 # filled to its spill level (the 16 m cell below)


def test_lidar_url_and_licence_survive_a_no_coverage_block_first():
    from provenance import merge_sources, source_summary
    island = dict(block=[1755000, 5470000, 1760000, 5475000], sources=dict(dem_2025=dict(ok=False, no_coverage=True, error="none")))
    town = dict(block=[1765000, 5465000, 1770000, 5470000], sources=dict(dem_2025=dict(
        ok=True, collection="https://example/collection.json", licence="CC-BY-4.0", sha256="aa", fetched="t")))
    s = source_summary(merge_sources([island, town])["dem_2025"])   # Kapiti Island's block comes first
    assert s["url"] and s["licence"], s


def test_partial_district_run_is_not_published():
    from check_complete import problems
    planned = [dict(xmin=1, ymin=2), dict(xmin=3, ymin=4)]
    assert problems(planned, {"1_2", "3_4"}, "", 2) == []
    assert problems(planned, {"1_2"}, "", 2)                      # a block failed
    assert problems(planned, {"1_2", "3_4"}, "1_2,3_4", 2)        # run limited with `only`
    assert problems(planned[:1], {"1_2"}, "", 2)                  # planned fewer than the district


def test_inland_parcel_smaller_than_linz_is_reported_not_hidden_as_clipped():
    from shapely.geometry import LineString, box
    from overlays import split_clipped
    edge = LineString([(0, 0), (0, 1000)])                          # the district boundary
    linz = {1: box(-30, 0, 50, 50), 2: box(500, 500, 550, 550),     # LINZ parcel 1 crosses the boundary
            3: box(40, 600, 3000, 2000)}                            # 3 is large but lies wholly inside the district
    clipped, other = split_clipped({1: -400.0, 2: -5.0, 3: -4e6}, linz, edge)
    assert set(clipped) == {1} and set(other) == {2, 3}


def test_flat_sea_cells_inside_a_coarse_land_cell_are_still_sea():
    import numpy as np
    import measures as M
    dem = np.full((40, 40), 3.0, np.float32); dem[:, :15] = -0.56          # flattened sea west of x = 15
    dem[20, 30] = -0.56                                                     # an isolated low cell inland: not sea
    dem[:, 15] = 0.2                                                        # a low beach beside the sea: still land
    coarse = np.zeros_like(dem, bool); coarse[:, :10] = True                # the 10 m grid's sea stops 5 m short
    sea = M.extend_sea(coarse, dem)
    assert sea[:, :15].all() and not sea[:, 15:].any()                     # includes the isolated cell staying land


def test_water_main_ties_go_to_the_largest_and_whole_numbers_are_integers():
    from shapely.geometry import LineString, box
    from overlays import nearest_item, largest_diameter, as_int
    parcel = box(0, 0, 20, 20)
    pipes = [(LineString([(5, -5), (5, 30)]), {"asset_id": "A", "nominal_diameter": 100}),
             (LineString([(15, -5), (15, 30)]), {"asset_id": "B", "nominal_diameter": 560})]
    assert nearest_item(pipes, [0, 1], parcel, prefer=largest_diameter)[1]["asset_id"] == "B"
    assert as_int(1964.0) == 1964 and isinstance(as_int(5.0), int) and as_int(None) is None and as_int(2.5) == 2.5


def test_source_check_reports_field_count_and_edit_changes():
    from source_check import compare
    old = {"zones": dict(fields=["A:String", "B:Double"], count=412, last_edit=1),
           "dem_2025": dict(items=19, sha256="x"), "gone": dict(count=1)}
    new = {"zones": dict(fields=["A:String", "C:String"], count=420, last_edit=2),
           "dem_2025": dict(items=19, sha256="y"), "fresh": dict(count=1)}
    out = "\n".join(compare(old, new))
    for s in ("fields changed", "count 412 → 420", "data edited", "catalogue changed", "`gone`: no longer checked", "`fresh`: new"):
        assert s in out, (s, out)
    assert compare(old, old) == []
    assert compare({"nz_dem_1m": dict(items=1, sha256="a")}, {"nz_dem_1m": dict(items=2, sha256="b")}) == []  # national: never flagged


def test_no_lidar_on_a_parcel_gives_empty_values_not_zero():
    import numpy as np
    import measures as M
    nan = np.full(10, np.nan)
    st = M.lidar_parcel_stats(nan, np.zeros(10, bool), 1.0, np.ones(10, bool), nan, np.zeros(10, bool), nan, np.zeros(10, bool))
    assert st["lidar_coverage_pct"] == 0.0 and all(st[k] is None for k in st if k != "lidar_coverage_pct"), st
    sea = np.ones(10, bool)                               # an island: no land cells, all sea
    assert M.lidar_parcel_stats(nan, sea, 1.0, np.ones(10, bool), nan, np.zeros(10, bool), nan, np.zeros(10, bool))["lidar_coverage_pct"] == 0.0
    z = np.arange(10.0); dz = np.full(10, np.nan)          # 2025 LiDAR but no 2021
    st = M.lidar_parcel_stats(z, np.zeros(10, bool), 1.0, np.ones(10, bool), np.zeros(10), np.zeros(10, bool), dz, np.ones(10, bool))
    assert st["dz_2021_2025_clear_pct"] is None and st["open_ground_slope_lt5_m2"] == 10


def test_ties_use_a_5_cm_tolerance():
    from shapely.geometry import Point, box
    from overlays import nearest_item
    parcel = box(0, 0, 1, 1)
    items = [(Point(11, 0.5), {"asset_id": "C"}), (Point(11.03, 0.5), {"asset_id": "A"}), (Point(11.06, 0.5), {"asset_id": "D"}),
             (Point(13, 0.5), {"asset_id": "B"})]
    d, p, tied = nearest_item(items, [0, 1, 2, 3], parcel)
    assert tied == ["A", "C"] and p["asset_id"] == "A"                  # 6 cm farther is not a tie


def test_district_sea_mask():
    import numpy as np
    from district_flow import sea_mask
    z = np.array([[-0.56, 2.0, -0.4, 0.6], [5.0, -1.005, 0.3, 0.5]])
    z8 = np.array([[np.nan, 2.1, -0.3, np.nan], [5.1, np.nan, np.nan, np.nan]])
    assert sea_mask(z, z8).tolist() == [[True, False, False, False], [False, True, True, True]]   # 0.6 m is land


def test_partial_runs_with_failed_sources_are_refused():
    from check_complete import problems
    planned = [dict(xmin=1, ymin=2)]
    assert problems(planned, {"1_2"}, "", 1, {"1_2": []}) == []
    assert problems(planned, {"1_2"}, "", 1, {"1_2": ["nonprimary_parcels"]})
    two = [dict(xmin=1, ymin=2), dict(xmin=3, ymin=4)]
    assert problems(two, {"1_2", "3_4"}, "", 2, {}, {"1_2": "aa", "3_4": "aa"}) == []
    assert problems(two, {"1_2", "3_4"}, "", 2, {}, {"1_2": "aa", "3_4": "bb"})   # a patch must not mix district-flow grids


def test_district_outline_closes_an_open_coastal_boundary_at_sea():
    from shapely.geometry import LineString, Point
    from overlays import district_polygon
    # an inland boundary from the coast at (100, 0) round to the coast at (100, 100), open along the coast (x = 100)
    d = district_polygon([LineString([(100, 0), (300, 0), (300, 50)]), LineString([(300, 50), (300, 100), (100, 100)])], sea_x=-50)
    assert d.contains(Point(200, 50)) and d.contains(Point(0, 50)) and not d.contains(Point(400, 50))
    assert d.is_empty is False and district_polygon([LineString([(0, 0), (1, 1)]), LineString([(5, 5), (6, 6)])]).is_empty


def test_coastal_land_below_sea_level_still_drains_into_the_sea():
    import numpy as np
    from rasterio.transform import from_origin
    from flow import flow_routing
    z = np.full((5, 6), 2.0, np.float32); z[:, 1] = -0.3              # a strip of land below 0 m beside the sea
    z[:, 0] = np.nan                                                  # the sea
    acc, trunc, step = flow_routing(z, from_origin(0, 5, 1, 1))
    assert float(np.nanmax(acc[:, 1])) <= 3, acc[:, 1]                # each low cell drains west into the sea, not along the strip


def test_coverage_is_never_0_when_a_parcel_has_lidar():
    import numpy as np
    import measures as M
    z = np.full(100000, np.nan); z[:11] = 191.0                       # 11 cells on a large parcel
    st = M.lidar_parcel_stats(z, np.zeros(z.size, bool), 1.0, np.ones(z.size, bool), np.zeros(z.size), np.zeros(z.size, bool),
                              np.full(z.size, np.nan), np.zeros(z.size, bool))
    assert st["lidar_coverage_pct"] == 0.1


def _outline():
    import json
    from shapely.geometry import shape
    from overlays import district_outline
    f = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "district_outline.json")))
    return district_outline([shape(g) for g in f["lines"]], [shape(g) for g in f["ward"]], [shape(g) for g in f["stats"]])


def test_real_district_outline_takes_in_kapiti_island_and_land_the_line_misses_but_not_neighbours():
    # fixture: KCDC's boundary line, its whole-district ward and Stats NZ's polygon, fetched 8 Nov 2026 (T-65, T-70)
    from shapely.geometry import Point, box
    o = _outline()
    assert 1900e6 < o.area < 1960e6  # land 731 km2 plus the sea loop
    assert o.contains(Point(1759216, 5474823))  # Section 3 Block I Kapiti SD, on Kapiti Island
    assert o.contains(Point(1760145, 5472149)) and o.contains(Point(1761935, 5478818))  # Motungarara islets; a rock off Kapiti Island (neither polygon has them)
    assert o.contains(Point(1779720, 5462958))  # Part Blk III Akatarawa SD: inside the ward and Stats NZ, cut by the line
    # Lot 2 DP 10208 (3910395), Upper Hutt side: only the line puts land of it inside (sixth review): under 100 m2 here
    near = box(1790000, 5455000, 1800000, 5470000)
    import json
    from shapely.geometry import shape
    f = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "district_outline.json")))
    w, s = shape(f["ward"][0]), shape(f["stats"][0])
    land = o.intersection(near)
    assert land.difference(w).difference(s).area < 2000  # no land that both polygons leave out (only sea-loop rounding)
    for p in [(1758500, 5449000), (1790000, 5500000), (1790000, 5445000)]:  # Pukerua Bay (Porirua), Levin, Upper Hutt side
        assert not o.contains(Point(*p)), p


def test_parcel_belongs_to_the_district_by_its_point_or_a_real_part_of_it():
    from shapely.geometry import box
    import overlays as ov
    district = box(0, 0, 1000, 1000)
    def f(i, g): return dict(properties=dict(id=i, appellation=str(i)), geometry=g.__geo_interface__)
    parcels = [f(1, box(100, 100, 200, 200)),        # inside
               f(2, box(700, 0, 1700, 1000)),        # 30% inside, point outside: kept
               f(3, box(998, 0, 10998, 1000)),       # 2,000 m2 inside, 0.02% of the parcel: kept (an area floor only)
               f(4, box(999.5, 0, 1019.5, 100)),     # 50 m2 inside: a digitising sliver
               f(5, box(2000, 0, 2100, 100)),        # outside
               f(6, box(999.05, 0, 1099.05, 1000))]  # 950 m2 inside: just under the floor
    inside, outside = ov.split_by_district(parcels, district)
    assert [p["properties"]["id"] for p in inside] == [1, 2, 3]
    assert [p["properties"]["district_share_pct"] for p in inside] == [100.0, 30.0, 0.0]
    assert [o["id"] for o in outside] == [4, 5, 6]
    assert ov.district_share(box(990, 0, 1090, 20), district) is None  # 200 m2



def test_district_land_is_where_two_of_three_boundaries_agree_and_the_sea_comes_from_the_line():
    from shapely.geometry import LineString, Point, box
    import overlays as ov
    # the line runs round land x 0..1000 (open on the coast at x=0) and closes at sea (sea_x); the ward reaches
    # 60 m further east than the line, Stats NZ 20 m further, and only the line takes in a 40 m strip in the south
    line = [LineString([(0, 1000), (1000, 1000)]), LineString([(1000, 1000), (1000, -40), (0, -40)])]
    ward, stats = [box(0, 0, 1060, 1000)], [box(0, 0, 1020, 1000)]
    o = ov.district_outline(line, ward, stats, sea_x=-5000)
    assert o.contains(Point(500, 500)) and o.contains(Point(-3000, 500))     # land all three agree on; the sea
    assert o.contains(Point(1010, 500))                                      # ward and Stats NZ agree: land
    assert not o.contains(Point(1040, 500))                                  # the ward alone
    assert not o.contains(Point(500, -20))                                   # the line alone, a 40 m strip on land
    assert ov.district_outline(line, [], stats).is_empty and ov.district_outline(line, ward, []).is_empty


def test_linz_parcels_missing_from_the_mirror_are_counted_once_and_only_in_the_district():
    from shapely.geometry import box
    import overlays as ov
    def f(i, g): return dict(properties=dict(id=i), geometry=g.__geo_interface__)
    by_id = {1: f(1, box(10, 10, 20, 20)), 2: f(2, box(30, 30, 40, 40)), 3: f(3, box(5000, 10, 5010, 20))}
    district, block = box(0, 0, 1000, 1000), box(0, 0, 100, 100)
    # 1 is in the mirror (assigned to whichever block); 3 lies outside the district
    assert [m["id"] for m in ov.linz_not_in_mirror(by_id, {1}, block, district)] == [2]
    assert ov.linz_not_in_mirror(by_id, {1}, box(500, 500, 600, 600), district) == []
    assert ov.linz_not_in_mirror(by_id, {1}, box(4900, 0, 5100, 100), district) == []  # in the block, outside the district


def test_parcels_source_fails_if_linz_returns_none_of_the_blocks_parcels():
    import overlays as ov
    assert ov.parcels_error(True, [1, 2], 0, None) == "LINZ returned none of the block's parcels"
    assert ov.parcels_error(True, [1, 2], 2, None) is None
    assert ov.parcels_error(False, [1, 2], 0, "LINZ_API_KEY not set") == "LINZ_API_KEY not set"
    assert ov.parcels_error(True, [], 0, None) is None


def test_lidar_catalogue_retries_checks_status_and_only_no_coverage_is_not_a_failure():
    import requests, lidar_catalogue as lc
    calls = []
    class R:
        def __init__(self, code): self.code = code
        def raise_for_status(self):
            if self.code >= 400: raise requests.exceptions.HTTPError(str(self.code))
        def json(self): return {"ok": 1}
    seq = [requests.exceptions.ConnectionError("x"), R(503), R(200)]
    def get(url, timeout):
        calls.append(url); x = seq.pop(0)
        if isinstance(x, Exception): raise x
        return x
    old = requests.get; requests.get = get
    try:
        assert lc.get_json("u", wait=0) == {"ok": 1} and len(calls) == 3
        seq[:] = [R(500)] * 4
        try: lc.get_json("u", wait=0); assert False, "an HTTP error must not pass"
        except requests.exceptions.HTTPError: pass
    finally: requests.get = old
    def nocov(): raise lc.NoCoverage("none")
    def broken(): return {}["links"]
    assert lc.source_entry(nocov) == dict(ok=False, no_coverage=True, error="none")
    e = lc.source_entry(broken)
    assert e["ok"] is False and "no_coverage" not in e
    assert lc.source_entry(lambda: dict(sha256="s")) == dict(ok=True, sha256="s")


def test_publishing_reads_each_blocks_flow_grid_and_refuses_a_block_without_one():
    import json, tempfile, check_complete as cc
    d = tempfile.mkdtemp()
    for b, sha in [("1_1", "a"), ("2_2", "b"), ("3_3", None)]:
        os.makedirs(os.path.join(d, "block-" + b))
        open(os.path.join(d, "block-" + b, "units.parquet"), "w").close()
        src = {"district_flow": {"sha256": sha}} if sha else {}
        if b == "1_1": src.update(dem_2025=dict(ok=False, no_coverage=True), zones=dict(ok=False, error="x"), ww_node=dict(ok=True))
        json.dump({"sources": src}, open(os.path.join(d, "block-" + b, "provenance.json"), "w"))
    os.makedirs(os.path.join(d, "block-4_4")); open(os.path.join(d, "block-4_4", "units.parquet"), "w").close()  # no provenance
    present, failed, shas = cc.read_blocks(d)
    assert present == {"1_1", "2_2", "3_3", "4_4"} and shas == {"1_1": "a", "2_2": "b", "3_3": None, "4_4": None}
    assert failed == {"1_1": ["zones"], "2_2": [], "3_3": [], "4_4": ["provenance.json missing"]}  # no coverage is not a failure
    planned = [dict(xmin=x, ymin=x) for x in (1, 2, 3, 4)]
    p = " ".join(cc.problems(planned, present, "", 4, failed, shas))
    assert "2 blocks have no district-flow record" in p and "2 different district-flow grids" in p
    assert "2 blocks have failed sources" in p and "provenance.json missing" in p


def test_every_column_built_on_lidar_lists_the_sea_mask_and_the_share_lists_the_outline():
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "service"))
    import catalogue as c
    for col in ["open_ground_m2", "roof_area_m2", "horizon_max_deg", "upslope_area_m2", "wind_rel_height_m",
                "lidar_coverage_pct", "winter_sun_hours", "ground_mean_m"]:
        src = c.column_sources(col)
        assert src and "sea_mask" in src, (col, src)
    assert "district_outline" in c.column_sources("district_share_pct")


def test_source_check_flags_a_missing_linz_key():
    import source_check as sc
    old = os.environ.pop("LINZ_API_KEY", None)
    try: sc.linz(50823); assert False, "a missing key must be flagged"
    except RuntimeError as e: assert "LINZ_API_KEY" in str(e)
    finally:
        if old is not None: os.environ["LINZ_API_KEY"] = old


def test_building_values_are_empty_not_0_where_the_outlines_do_not_reach():
    # KCDC's 2021 outlines have none on Kapiti Island or outside the district; islands with houses read 0 (seventh review)
    from shapely.geometry import box
    import overlays as ov
    cover = ov.building_cover(dict(xmin=0, ymin=0, xmax=1000, ymax=1000), box(-500, 0, 800, 1000))
    assert cover.bounds == (0.0, 0.0, 800.0, 1000.0)                      # the extent, within the district
    full = {k: 7 for k in ov.BUILDING_COLUMNS}
    r = ov.withhold_uncovered_buildings(dict(full), box(100, 100, 200, 200), cover)
    assert all(r[k] == 7 for k in ov.BUILDING_COLUMNS) and r["buildings_coverage_pct"] == 100.0
    r = ov.withhold_uncovered_buildings(dict(full), box(790, 0, 810, 100), cover)   # half outside the district
    assert all(r[k] is None for k in ov.BUILDING_COLUMNS) and r["buildings_coverage_pct"] == 50.0
    r = ov.withhold_uncovered_buildings(dict(full), box(701, 0, 801, 100), cover)   # 99% covered: kept
    assert r["buildings_coverage_pct"] == 99.0 and r["open_ground_m2"] == 7
    r = ov.withhold_uncovered_buildings(dict(full), box(702, 0, 802, 100), cover)   # 98%: empty
    assert r["open_ground_m2"] is None
    assert ov.withhold_uncovered_buildings({}, box(700, 0, 830, 100), cover)["buildings_coverage_pct"] == 76.9
    r = ov.withhold_uncovered_buildings(dict(full), box(100, 100, 200, 200), None)   # extent unknown
    assert r["building_2021_m2"] is None and r["buildings_coverage_pct"] == 0.0
    for k in ["building_2021_m2", "open_ground_m2", "open_ground_slope_lt5_m2", "canopy_gt3m_open_pct", "open_ground_clear_pct",
              "winter_sun_hours_open_mean", "roof_flat_m2", "roof_solar_rel_pct", "level_open_cut_m3", "platform_15m_earthworks_min_m3"]:
        assert k in ov.BUILDING_COLUMNS, k


def test_membership_floor_point_and_share_precision():
    from shapely.geometry import box
    import overlays as ov
    district = box(0, 0, 100, 100)
    assert ov.district_share(box(90, 0, 1090, 100), district) == 1.0       # exactly 1,000 m2 inside: kept
    assert ov.district_share(box(90.01, 0, 1090.01, 100), district) is None  # 999 m2
    frame = box(-200, -200, 300, 300).difference(box(-5, -5, 105, 105))       # a frame round the district, 5 m clear
    assert frame.centroid.within(district) and ov.district_share(frame, district) is None  # its centre is not a point of it
    assert ov.district_share(box(66.7, 0, 166.7, 100), box(0, 0, 100, 10000)) == 33.3  # one decimal place


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
