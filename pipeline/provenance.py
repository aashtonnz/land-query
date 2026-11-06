"""Source provenance per block, and per query row (T-41).

Each fetcher records, for every source it fetches, the URL, licence, fetch time (UTC), sha256 and feature count of
what it fetched for one block's fetch window. The district merge keeps those values per block, so a query row can carry
the sha256 and fetch time of exactly the data its own block was compiled from.
"""
import datetime as dt

FIELDS = ("sha256", "fetched", "features")


def utc_now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def block_id_of(prov):
    """The block id as units.block_id spells it (xmin_ymin_size)."""
    if prov.get("block_id"): return prov["block_id"]
    x0, y0, x1, _ = prov["block"]
    return f"{x0}_{y0}_{x1 - x0}"


def merge_sources(block_provs):
    """District provenance: one entry per source, with its per-block sha256, fetch time and feature count.

    Feature counts stay per block: fetch windows overlap, so a sum across blocks would count features twice."""
    out = {}
    for p in block_provs:
        bid = block_id_of(p)
        for k, v in p["sources"].items():
            e = out.setdefault(k, dict(url=v.get("url") or v.get("collection"), licence=v.get("licence"),
                                       blocks=0, failed_blocks=0, fetched_first=None, fetched_last=None, by_block={}))
            e["blocks"] += 1
            if not v.get("ok", True):
                e["failed_blocks"] += 0 if v.get("no_coverage") else 1
                continue
            t = v.get("fetched")
            if t:
                e["fetched_first"] = min(filter(None, [e["fetched_first"], t]))
                e["fetched_last"] = max(filter(None, [e["fetched_last"], t]))
            e["by_block"][bid] = {f: v.get(f) for f in FIELDS}
    return out


def source_summary(entry):
    """What a query reports once per source: where it came from and under what licence."""
    if "by_block" not in entry:  # a single compiled block: the entry is that block's own record
        return dict({f: entry.get(f) for f in ("licence", "sha256", "fetched", "features")},
                    url=entry.get("url") or entry.get("collection"))
    return {f: entry.get(f) for f in ("url", "licence", "blocks", "fetched_first", "fetched_last")}


def row_sources(PROV, keys, block_id):
    """sha256 and fetch time of each source as fetched for this row's block."""
    out = {}
    for k in keys:
        e = PROV.get(k)
        if not e: continue
        v = e["by_block"].get(block_id) if "by_block" in e else e
        if v and v.get("sha256"): out[k] = dict(sha256=v["sha256"], fetched=v.get("fetched"))
    return out
