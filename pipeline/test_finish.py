"""Tests for finish.py, light enough for the finish workflow (pandas and shapely only). Run: python3 test_finish.py"""
import os, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overlays as ov
from finish import finish_frame, limits


def frame():
    base = dict(unit_id=1, buildings_coverage_pct=100.0, coverage_pct=100.0, lidar_coverage_pct=100.0,
                ww_pipe_condition_grade=3.0, ww_pipe_year=1980.0, rbl_in_parcel_n=2.0, upslope_area_max_m2=500.0,
                upslope_area_truncated=False, flow_path_m=12.0, **{k: 5.0 for k in ov.BUILDING_COLUMNS})
    rows = [dict(base), dict(base, unit_id=2, coverage_pct=50.0), dict(base, unit_id=3, lidar_coverage_pct=40.0),
            dict(base, unit_id=4, ww_pipe_condition_grade=0.0, ww_pipe_year=None),
            dict(base, unit_id=5, **{k: None for k in ov.BUILDING_COLUMNS})]   # emptied by an older rule
    return pd.DataFrame(rows)


def test_finish_applies_the_rules_and_keeps_rows_columns_and_whole_numbers():
    df = frame()
    out, changed = finish_frame(df, ["unit_id", "ww_pipe_condition_grade", "ww_pipe_year"])
    assert list(out.columns) == list(df.columns) and list(out["unit_id"]) == [1, 2, 3, 4, 5]
    assert str(out["ww_pipe_condition_grade"].dtype) == "Int64" and str(out["ww_pipe_year"].dtype) == "Int64"
    assert out.loc[1, "building_2021_m2"] is pd.NA or pd.isna(out.loc[1, "building_2021_m2"])
    assert pd.isna(out.loc[2, "flow_path_m"]) and out.loc[2, "building_2021_m2"] == 5
    assert pd.isna(out.loc[3, "ww_pipe_condition_grade"]) and pd.isna(out.loc[3, "ww_pipe_year"])
    assert out.loc[0, "flow_path_m"] == 12 and out.loc[0, "ww_pipe_condition_grade"] == 3
    assert changed["building_2021_m2"] == 1 and changed["flow_path_m"] == 1 and changed["ww_pipe_condition_grade"] == 1
    assert "ww_pipe_year" not in changed                         # 1980.0 and 1980 are the same value
    again, changed2 = finish_frame(out, ["unit_id", "ww_pipe_condition_grade", "ww_pipe_year"])
    assert changed2 == {}                                         # idempotent


def test_finish_reports_what_only_a_rebuild_can_do():
    out, _ = finish_frame(frame(), ["unit_id"])
    missing, restorable = limits(out)
    assert "unmapped_structure_m2" in missing                     # a pending column, absent here
    assert restorable == 1                                        # parcel 5: covered, but emptied by an older rule
    assert "unmapped_structure_m2" in ov.LIDAR_FLOW_COLUMNS       # empty under 99% LiDAR once it exists


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
