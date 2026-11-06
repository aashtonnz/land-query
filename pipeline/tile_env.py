"""Block and fetch-window settings shared by the pipeline scripts.

A block is a square of TILE_SIZE metres (default 1000) with its south-west corner at TILE_XMIN, TILE_YMIN (NZTM2000).
Each parcel belongs to the block containing its representative point. fetch_parcels_kcdc.py writes the fetch window
(the block grown to cover those parcels, capped at MAX_BUFFER metres beyond the block) to data/fetch_bbox.json; the
other fetchers and the compiler read it, so every parcel is computed whole unless it is larger than the cap.
"""
import json, os

X = int(os.environ.get("TILE_XMIN", 1769000))
Y = int(os.environ.get("TILE_YMIN", 5468400))
SIZE = int(os.environ.get("TILE_SIZE", 1000))
MAX_BUFFER = int(os.environ.get("MAX_BUFFER", 1000))
BLOCK = (X, Y, X + SIZE, Y + SIZE)
BLOCK_ID = f"{X}_{Y}_{SIZE}"


def fetch_bbox(out="data"):
    """The fetch window for this block: from data/fetch_bbox.json if written, otherwise the block itself."""
    p = os.path.join(out, "fetch_bbox.json")
    return tuple(json.load(open(p))["bbox"]) if os.path.exists(p) else BLOCK
