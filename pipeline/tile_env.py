"""Block and fetch-window settings shared by the pipeline scripts.

A block is a square of TILE_SIZE metres (default 1000) with its south-west corner at TILE_XMIN, TILE_YMIN (NZTM2000).
Each parcel belongs to the block containing its representative point. fetch_parcels_kcdc.py writes the fetch window
(the block grown to cover those parcels, capped at MAX_BUFFER metres beyond the block) to data/fetch_bbox.json; the
other fetchers and the compiler read it, so every parcel is computed whole unless it is larger than the cap.
"""
import json, os, re

X = int(os.environ.get("TILE_XMIN", 1769000))
Y = int(os.environ.get("TILE_YMIN", 5468400))
SIZE = int(os.environ.get("TILE_SIZE", 1000))
MAX_BUFFER = int(os.environ.get("MAX_BUFFER", 1000))
# LiDAR is read this far beyond the fetch window, so shadows (to 300 m) and obstruction near its edge see what is beyond
LIDAR_CONTEXT_M = int(os.environ.get("LIDAR_CONTEXT_M", 300))
BLOCK = (X, Y, X + SIZE, Y + SIZE)
BLOCK_ID = f"{X}_{Y}_{SIZE}"


def fetch_bbox(out="data"):
    """The fetch window for this block: from data/fetch_bbox.json if written, otherwise the block itself."""
    p = os.path.join(out, "fetch_bbox.json")
    return tuple(json.load(open(p))["bbox"]) if os.path.exists(p) else BLOCK


PERSON_HINTS = re.compile(r"[\w.%+-]+@[\w-]+\.[\w.-]+|\bx\d{3,4}\b|\b(?:by|from|contact)\s+[A-Z][a-z]+", re.I)


def scrub_copyright(text):
    """Layer copyright text, unless it names or contacts a person (D-12: never data about people)."""
    text = (text or "")[:200]
    return "[withheld: names a person]" if PERSON_HINTS.search(text) else text


def ll_envelope(bbox):
    """Lon/lat envelope of an NZTM box from all four corners (grid convergence makes two corners miss parts)."""
    from pyproj import Transformer
    tr = Transformer.from_crs(2193, 4326, always_xy=True)
    x0, y0, x1, y1 = bbox
    lons, lats = tr.transform([x0, x1, x0, x1], [y0, y0, y1, y1])
    return min(lons), min(lats), max(lons), max(lats)


def lidar_bbox(out="data"):
    x0, y0, x1, y1 = fetch_bbox(out); c = LIDAR_CONTEXT_M
    return (x0 - c, y0 - c, x1 + c, y1 + c)
