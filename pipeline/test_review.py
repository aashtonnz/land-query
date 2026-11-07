"""Regression checks for fixes from the fresh-eyes review (T-39). Run: python3 test_review.py"""
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
    from overlays import nearest_item
    parcel = box(0, 0, 20, 20)
    a = (LineString([(10, -5), (10, 10)]), {"asset_id": "KWWP001431", "condition_grade": 4})
    b = (LineString([(10, 10), (10, 30)]), {"asset_id": "KWWP001430", "condition_grade": 2})
    assert nearest_item([a, b], [0, 1], parcel)[1]["asset_id"] == nearest_item([b, a], [0, 1], parcel)[1]["asset_id"] == "KWWP001430"


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
    import numpy as np
    from rasterio.transform import from_origin
    from flow import flow_routing
    z = np.tile(np.arange(20, 0, -1, dtype=np.float32)[:, None], (1, 5))  # slopes down to the south
    z[0:3, :] = np.nan                                                    # a survey gap upslope, at the north end
    outside = np.full(z.shape, np.nan); outside[0:3, :] = 30.0           # known higher ground there
    acc = flow_routing(z, from_origin(0, 20, 1, 1), outside=outside)[0]
    assert float(np.nansum(acc[-1, :])) == np.isfinite(z).sum()           # all of it reaches the south edge


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
