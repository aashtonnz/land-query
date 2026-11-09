"""LiDAR catalogue requests and how a survey's outcome is recorded (T-62, T-65: split from fetch_lidar.py to be tested)."""
import time
import requests


class NoCoverage(Exception):
    """No survey tile touches the window: not a failure. A separate class, so a malformed catalogue response, such as a
    KeyError, can never pass as "no coverage" (T-62)."""


def get_json(url, tries=4, wait=10):
    """GET and parse JSON, retried on connection errors, HTTP errors and bad JSON, like the downloads (T-62)."""
    for attempt in range(tries):
        try:
            r = requests.get(url, timeout=60); r.raise_for_status(); return r.json()
        except (requests.exceptions.RequestException, ValueError):
            if attempt == tries - 1: raise
            time.sleep(wait * (attempt + 1))


def source_entry(read, *args):
    """The provenance entry for one survey: ok with read()'s metadata; no coverage (not a failure); or failed."""
    try: return dict(ok=True, **read(*args))
    except NoCoverage as e: return dict(ok=False, no_coverage=True, error=str(e))
    except Exception as e: return dict(ok=False, error=str(e)[:300])


NO_DATA_FLOOR = -1000.0   # below any real height in New Zealand (the Martha pit at Waihi reaches about -101 m; T-111)


def no_data_to_nan(part, nodata):
    """Heights with the file's no-data value, or any marker at or below NO_DATA_FLOOR, as NaN: a boundless windowed read
    does not mask the file's own no-data value, so a gap in a mosaic came back as -9999 m (T-107)."""
    import numpy as np
    part = part.astype("float32", copy=True)
    if nodata is not None: part[part == np.float32(nodata)] = np.nan
    part[part <= NO_DATA_FLOOR] = np.nan
    return part


def read_sheets(hrefs, bbox, res=1.0):
    """The window bbox at res from each sheet in place (paths or URLs), the first sheet with data winning on an overlap;
    no-data never becomes a height (T-107)."""
    import numpy as np, rasterio
    from rasterio.windows import from_bounds
    x0, y0, x1, y1 = bbox
    W, H = int(round((x1 - x0) / res)), int(round((y1 - y0) / res))
    arr = np.full((H, W), np.nan, np.float32)
    for h in hrefs:
        with rasterio.open(h) as src:
            part = src.read(1, window=from_bounds(x0, y0, x1, y1, src.transform), out_shape=(H, W), boundless=True,
                            fill_value=np.nan, masked=True).filled(np.nan)
            part = no_data_to_nan(part, src.nodata)
        fill = np.isnan(arr) & np.isfinite(part); arr[fill] = part[fill]
    return arr
