"""Tests for the map build (site/build_map.py) that need no network. Run: python3 site/test_site.py"""
import importlib.util, os, sys
from shapely.geometry import box
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], "/nonexistent"]
spec = importlib.util.spec_from_file_location("build_map", os.path.join(HERE, "build_map.py"))
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)


def test_only_the_sea_part_of_a_part_water_parcel_is_drawn_as_water():
    land = [box(0, 0, 100, 100)]
    geoms = {1: box(50, 0, 150, 100), 2: box(90, 10, 110, 20), 3: box(300, 300, 310, 310)}   # 2 and 3 reach past the outline
    P = {1: {}, 2: {}, 3: {}}
    out = B.sea_parts(P, geoms, {1: 50.0, 2: 0, 3: None}, land)
    assert len(out) == 1 and abs(out[0].area - 5000) < 1 and out[0].bounds[0] == 100   # half of parcel 1; nothing for 2 (measured 0) or 3 (unknown)


def test_the_page_script_parses():
    """A syntax error in map.js leaves the page stuck on "Loading the map" (10 Nov 2026: a comment swallowed a line's end)."""
    import shutil, subprocess
    if shutil.which("node"): subprocess.run(["node", "--check", os.path.join(HERE, "map.js")], check=True)


def test_search_files_take_parcels_without_an_address_and_split_large_groups():
    import json, tempfile
    B.OUT = tempfile.mkdtemp()
    rows = [(1, 0, 0, "n", "Lot 1 DP 100", float("nan")), (2, 5, 5, "n", "Lot 2 DP 100", "2 Kōwhai Road, Ōtaki"), (3, 9, 9, "n", None, None)]
    rows += [(10 + i, i, i, "n", f"Section {i} Block II", None) for i in range(4000)]
    keys = B.write_search_shards(iter(rows), max_bytes=20_000)
    assert "lot" in keys and "2kowha" in keys or "2ko" in keys, keys[:10]
    assert len([k for k in keys if k.startswith("sec")]) > 1                 # a large group is split by more letters
    every = [e for k in keys for e in json.load(open(os.path.join(B.OUT, "data", "search", k + ".json")))]
    assert {1, 2} <= {e[0] for e in every} and 3 not in {e[0] for e in every}   # nothing to search by: left out
    assert next(e for e in every if e[0] == 1)[4] == "Lot 1 DP 100"


def test_the_r2_upload_sends_every_file_once_and_keeps_the_newest_three_builds():
    """D-26: every data file under builds/BUILD/, with its type and a year's caching; older builds deleted."""
    import tempfile, threading
    import upload_r2 as U
    class Bucket:
        def __init__(self, keys): self.objs, self.lock, self.deletes = dict.fromkeys(keys), threading.Lock(), 0
        def put_object(self, Bucket, Key, Body, CacheControl, ContentType):
            with self.lock: assert Key not in self.objs; self.objs[Key] = (Body, CacheControl, ContentType)
        def list_objects_v2(self, Bucket, Prefix, Delimiter=None, ContinuationToken=None):
            keys = sorted(k for k in self.objs if k.startswith(Prefix))
            if Delimiter: return dict(CommonPrefixes=[dict(Prefix=p) for p in sorted({Prefix + k[len(Prefix):].split("/")[0] + "/" for k in keys})])
            after = [k for k in keys if ContinuationToken is None or k > ContinuationToken]   # paged by key, as a bucket pages
            page, more = after[:1500], len(after) > 1500
            return dict(Contents=[dict(Key=k) for k in page], IsTruncated=more, **(dict(NextContinuationToken=page[-1]) if more else {}))
        def delete_objects(self, Bucket, Delete):
            assert len(Delete["Objects"]) <= 1000; self.deletes += 1
            for o in Delete["Objects"]: self.objs.pop(o["Key"])
    old = [f"builds/2026111{d}000000/x{i}.bin" for d in range(4) for i in range(2500 if d == 0 else 2)]
    b = Bucket(old)
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "L0"))
    for name in ("meta.json", "L0/a.bin", "L0/b.bin"): open(os.path.join(d, name), "wb").write(b"x")
    assert U.upload(b, "bk", d, "20261116090000", threads=4) == 3
    assert b.objs["builds/20261116090000/L0/a.bin"] == (b"x", U.CACHE, "application/octet-stream")
    assert b.objs["builds/20261116090000/meta.json"][2] == "application/json"
    assert U.prune(b, "bk") == ["20261110000000", "20261111000000"]     # the first holds 2,500 files: 1,000 a request
    assert U.builds(b, "bk") == ["20261112000000", "20261113000000", "20261116090000"] and b.deletes == 4


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
