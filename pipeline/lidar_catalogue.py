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
