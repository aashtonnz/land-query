"""Known-answer tests for measures.py (T-37). Run: python3 test_measures.py"""
import datetime as dt, math
import numpy as np
from rasterio.transform import from_origin
import measures as M


def test_sun_noon_altitude():
    # at solar noon on the solstices, altitude = 90 - |latitude| ∓ 23.44 (Wellington, -41.29)
    for month, expect in ((6, 90 - 41.29 - 23.44), (12, 90 - 41.29 + 23.44)):
        best = max(M.sun_position(-41.29, 174.78, dt.datetime(2026, month, 21, tzinfo=dt.timezone.utc) - dt.timedelta(hours=12)
                                  + dt.timedelta(minutes=k))[1] for k in range(11 * 60, 13 * 60 + 30))
        assert abs(best - expect) < 0.3, (month, best, expect)


def test_sun_north_at_midwinter_noon():
    az, _ = M.sun_position(-41.29, 174.78, dt.datetime(2026, 6, 21, 0, 20, tzinfo=dt.timezone.utc))  # ~12:20 NZST
    assert az < 10 or az > 350, az


def test_shadow_length():
    dsm = np.zeros((100, 100), np.float32); dsm[40, :] = 10   # 10 m wall; sun due north at 45°
    shaded_rows = np.where(~M.sunlit(dsm, 0, 45)[:, 50])[0]
    assert shaded_rows.min() == 41 and shaded_rows.max() == 49, shaded_rows


def test_horizon_flat_and_wall():
    flat = np.zeros((200, 200), np.float32)
    assert max(M.horizon(flat, flat, 100, 100)) == 0
    wall = flat.copy(); wall[90, :] = 11.6   # 10 m above eye level, 10 m north
    hz = M.horizon(wall, flat, 100, 100)
    assert abs(hz[0] - 45) < 0.5, hz[0]


def test_flow_on_plane():
    rows, cols = 50, 20
    dem = np.tile(np.arange(rows, 0, -1, dtype=np.float64)[:, None], (1, cols))   # slopes down to the south
    acc = M.flow_accumulation(dem, from_origin(0, rows, 1, 1))
    assert abs(float(np.nanmax(acc)) - rows) <= 1, np.nanmax(acc)


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
