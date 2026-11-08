"""Computed measures from the LiDAR surfaces (T-37). All outputs are modelled or derived values, labelled as such
in SOURCES.md. Functions work on the block's 1 m rasters (north-up, square cells).

- Sun position: NOAA solar position equations.
- Shadows: a cell is shaded when the DSM along the sun's direction rises above the sun ray from that cell,
  searched out to MAX_SHADOW_M (obstacles farther away, such as distant ranges, are not counted).
- Overland flow: D8 flow accumulation on the 2024-25 DEM, every cell drained by priority-flood (flow.py).
- Horizon and sky view: rays in 16 directions from a point at eye height, to MAX_HORIZON_M.
- Wind exposure: surrounding obstruction share and relative elevation (an approximation of NZS 3604 site exposure
  and topographic class, not a wind zone determination).
"""
import math, datetime as dt
import numpy as np

MAX_SHADOW_M = 300
MAX_HORIZON_M = 500
EYE_M = 1.6


def sun_position(lat, lon, when_utc):
    """Solar azimuth (degrees clockwise from true north) and altitude (degrees) for a UTC datetime (NOAA)."""
    jd = when_utc.timestamp() / 86400.0 + 2440587.5
    jc = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + jc * (36000.76983 + jc * 0.0003032)) % 360
    m = 357.52911 + jc * (35999.05029 - 0.0001537 * jc)
    e = 0.016708634 - jc * (0.000042037 + 0.0000001267 * jc)
    mr = math.radians(m)
    c = math.sin(mr) * (1.914602 - jc * (0.004817 + 0.000014 * jc)) + math.sin(2 * mr) * (0.019993 - 0.000101 * jc) + math.sin(3 * mr) * 0.000289
    true_long = l0 + c
    app_long = true_long - 0.00569 - 0.00478 * math.sin(math.radians(125.04 - 1934.136 * jc))
    eps0 = 23 + (26 + (21.448 - jc * (46.815 + jc * (0.00059 - jc * 0.001813))) / 60) / 60
    eps = eps0 + 0.00256 * math.cos(math.radians(125.04 - 1934.136 * jc))
    decl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(app_long))))
    y = math.tan(math.radians(eps / 2)) ** 2
    l0r = math.radians(l0)
    eq_time = 4 * math.degrees(y * math.sin(2 * l0r) - 2 * e * math.sin(mr) + 4 * e * y * math.sin(mr) * math.cos(2 * l0r)
                               - 0.5 * y * y * math.sin(4 * l0r) - 1.25 * e * e * math.sin(2 * mr))
    minutes = when_utc.hour * 60 + when_utc.minute + when_utc.second / 60
    tst = (minutes + eq_time + 4 * lon) % 1440
    ha = tst / 4 - 180 if tst / 4 >= 0 else tst / 4 + 180
    latr, decr, har = map(math.radians, (lat, decl, ha))
    cz = max(-1, min(1, math.sin(latr) * math.sin(decr) + math.cos(latr) * math.cos(decr) * math.cos(har)))
    zen = math.degrees(math.acos(cz))
    if abs(math.sin(math.radians(zen))) < 1e-9: az = 0.0
    else:
        ca = (math.sin(latr) * cz - math.sin(decr)) / (math.cos(latr) * math.sin(math.radians(zen)))
        az = math.degrees(math.acos(max(-1, min(1, ca))))
        az = (az + 180) % 360 if ha > 0 else (540 - az) % 360
    return az, 90 - zen


def day_positions(lat, lon, month, day, year=2026, min_alt=3.0, step_min=60):
    """Sun positions on a day, every step_min minutes of NZ standard time (UTC+12), with altitude above min_alt."""
    out = []
    for k in range(0, 24 * 60, step_min):
        t = dt.datetime(year, month, day, tzinfo=dt.timezone.utc) + dt.timedelta(minutes=k) - dt.timedelta(hours=12)
        az, alt = sun_position(lat, lon, t)
        if alt > min_alt: out.append((k / 60, az, alt))
    return out


def _distances(maxd):
    """Search distances in metres: every metre close in, coarser farther out."""
    return np.unique(np.concatenate([np.arange(1, 30), np.arange(30, 100, 2), np.arange(100, maxd + 1, 5)])).astype(float)


def sunlit(dsm, az, alt, res=1.0, maxd=MAX_SHADOW_M):
    """Boolean array, True where the cell is in direct sun. NaN cells count as no obstacle."""
    h = np.where(np.isfinite(dsm), dsm, -1e9).astype(np.float32)
    shaded = np.zeros(h.shape, bool)
    t = math.tan(math.radians(alt)); a = math.radians(az)
    dx, dy = math.sin(a), math.cos(a)  # towards the sun: east is +col, north is -row
    H, W = h.shape
    for d in _distances(maxd):
        c, r = int(round(dx * d / res)), int(round(-dy * d / res))
        if abs(r) >= H or abs(c) >= W: continue
        rise = np.float32(d * t)
        src = h[max(0, r):H + min(0, r), max(0, c):W + min(0, c)]          # obstacle cells
        dst = (slice(max(0, -r), H + min(0, -r)), slice(max(0, -c), W + min(0, -c)))  # cells being tested
        shaded[dst] |= src > h[dst] + rise
    return ~shaded


from flow import flow_routing  # noqa: E402  (D8 flow: priority-flood, every cell drains)


def flow_accumulation(dem, transform):
    """D8 upslope area (m², counting the cell itself). See flow_routing."""
    return flow_routing(dem, transform)[0]


def horizon(dsm, dem, row, col, res=1.0, n=16, maxd=MAX_HORIZON_M):
    """Horizon elevation angles (degrees) in n directions from a point at eye height above ground."""
    H, W = dsm.shape
    z0 = dem[row, col] + EYE_M
    if not np.isfinite(z0): return None
    ds = _distances(maxd)
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = np.round(row - math.cos(a) * ds / res).astype(int); cc = np.round(col + math.sin(a) * ds / res).astype(int)
        ok = (rr >= 0) & (rr < H) & (cc >= 0) & (cc < W)
        if not ok.any(): out.append(0.0); continue
        z = dsm[rr[ok], cc[ok]]; d = ds[ok]
        ang = np.degrees(np.arctan2(z - z0, d)); ang = ang[np.isfinite(ang)]
        out.append(float(max(0.0, ang.max())) if ang.size else 0.0)
    return out


CLEAR_M = 0.5  # ground counts as open to the sky where the DSM is within this of the DEM (no tree, roof or fence above)


def ground_clear(dsm, dem, clear_m=CLEAR_M):
    """True where nothing stands above the ground (DSM within clear_m of the DEM); False under trees or where no data."""
    with np.errstate(invalid="ignore"):
        return (dsm - dem) <= clear_m


def unmapped_structures(dsm, dem, outlines, low=2.5, high=15.0, rough=0.2, k=3):
    """Cells of building-like structures that no 2021 outline covers (T-79, T-81): 2.5-15 m above the ground, on a
    surface that is locally a plane (a 3 x 3 plane fit leaves a residual under 0.2 m, so pitched roofs pass and tree
    crowns don't), at least 3 m wide (an opening removes the strips where a roof overhangs its outline), and more
    than 2 m from any outline. The interior found is then grown back by one cell, over cells still 2.5-15 m up, to
    give the footprint. KCDC's outlines miss some houses, even inside the area they cover (ninth review); the
    smoothness test used first (T-79) rejected roofs steeper than about 23 degrees (tenth review)."""
    from scipy.ndimage import uniform_filter, correlate, binary_opening, binary_dilation
    with np.errstate(invalid="ignore"):
        nd = dsm - dem
        d = np.where(np.isfinite(dsm), dsm, 0).astype(np.float64)
        n = k * k; h = k // 2; xs = np.arange(-h, h + 1, dtype=float); sxx = k * float((xs * xs).sum())
        m1 = uniform_filter(d, k, mode="nearest"); m2 = uniform_filter(d * d, k, mode="nearest")
        kx = np.tile(xs, (k, 1))
        sx = correlate(d, kx, mode="nearest"); sy = correlate(d, kx.T, mode="nearest")
        rss = n * (m2 - m1 * m1) - (sx * sx + sy * sy) / sxx   # residual of z = a + b x + c y over the k x k cells
        resid = np.sqrt(np.clip(rss, 0, None) / n)
        tall = (nd > low) & (nd < high) & np.isfinite(nd)
    near = binary_dilation(outlines, iterations=2)
    core = binary_opening(tall & (resid < rough) & ~near, structure=np.ones((3, 3), bool))
    return binary_dilation(core, structure=np.ones((3, 3), bool)) & tall & ~near


def largest_structure_m2(mask, cell_m2=1.0):
    """Area of the largest 8-connected patch of mask (0 if none)."""
    from scipy.ndimage import label
    lab, n = label(mask, structure=np.ones((3, 3), bool))
    return 0 if n == 0 else int(np.bincount(lab.ravel())[1:].max() * cell_m2)


def platform_centres(open_mask, k=15):
    """Cells at the centre of a k × k square lying wholly on open_mask (the parcel's open ground)."""
    from scipy.ndimage import binary_erosion
    return binary_erosion(open_mask, structure=np.ones((k, k), bool), border_value=0)


def viewpoint(open_mask, clear):
    """The open, clear-sky cell farthest from buildings, trees and the boundary: (row, col), or None if there is none."""
    from scipy.ndimage import distance_transform_edt
    ok = open_mask & clear
    if not ok.any(): return None
    d = distance_transform_edt(ok)
    return np.unravel_index(int(np.argmax(d)), d.shape)


def extend_sea(sea, dem, tol=0.005):
    """Grow a coarse sea mask over the 1 m DEM: cells at the survey's flat sea value (the most common value under the
    mask) that connect to the masked sea are sea too, so the shoreline cells the 10 m grid counts as land are caught."""
    from scipy.ndimage import binary_propagation
    v = dem[sea & np.isfinite(dem)]
    if v.size < 100: return sea
    vals, counts = np.unique(np.round(v, 3), return_counts=True)
    flat = vals[np.argmax(counts)]
    with np.errstate(invalid="ignore"):
        cand = sea | (np.abs(dem - flat) <= tol)
    return binary_propagation(sea, structure=np.ones((3, 3), bool), mask=cand)


def lidar_parcel_stats(z, sea, inside_frac, open_ground, slope, canopy, dz, clear):
    """Parcel figures that need LiDAR, all None when the parcel has no LiDAR cells (D-12: never 0 for "no data").

    z, sea, slope, canopy, dz and clear are the parcel's cells (1-D); open_ground marks open cells among them;
    inside_frac is the share of the parcel inside the LiDAR window (T-49, T-59)."""
    n = int(np.isfinite(z).sum())
    if n == 0:
        return dict(lidar_coverage_pct=0.0, open_ground_slope_lt5_m2=None, canopy_gt3m_open_pct=None,
                    dz_2021_2025_clear_pct=None, dz_2021_2025_clear_mean_m=None)
    og = open_ground & np.isfinite(z)
    both = np.isfinite(dz)                       # cells with 2021 and 2025 ground
    c = both & clear
    return dict(
        # never shown as 0 when the parcel has LiDAR cells (T-62: two large parcels with a few cells rounded to 0.0)
        lidar_coverage_pct=max(0.1, round(100 * float((np.isfinite(z) | sea).sum()) / z.size * inside_frac, 1)),
        open_ground_slope_lt5_m2=int((og & (slope < 5)).sum()),
        canopy_gt3m_open_pct=round(100 * float((canopy & og).sum()) / og.sum(), 1) if og.any() else None,
        dz_2021_2025_clear_pct=round(100 * float(c.sum()) / both.sum(), 1) if both.any() else None,
        dz_2021_2025_clear_mean_m=round(float(dz[c].mean()), 3) if c.sum() >= 50 else None)
