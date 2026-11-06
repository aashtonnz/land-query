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


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
