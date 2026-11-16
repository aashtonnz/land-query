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


def test_the_r2_upload_sends_changed_data_once_and_keeps_the_newest_three_builds():
    """D-26: every data file under builds/BUILD/ with its type and a year's caching, meta.json last; a build whose data
    is already there sends only meta.json; the newest three complete builds kept, incomplete ones deleted."""
    import tempfile, threading, itertools
    import upload_r2 as U
    clock = itertools.count(100)
    class Missing(Exception):
        response = {"Error": {"Code": "404"}}
    class Bucket:
        def __init__(self, keys): self.objs, self.lock, self.deletes, self.puts = {k: (b"", None, None, next(clock)) for k in keys}, threading.Lock(), 0, []
        def put_object(self, Bucket, Key, Body, CacheControl, ContentType):
            with self.lock: self.objs[Key] = (Body, CacheControl, ContentType, next(clock)); self.puts.append(Key)
        def head_object(self, Bucket, Key):
            if Key not in self.objs: raise Missing()
            return dict(LastModified=self.objs[Key][3])
        def list_objects_v2(self, Bucket, Prefix, Delimiter=None, ContinuationToken=None):
            keys = sorted(k for k in self.objs if k.startswith(Prefix))
            if Delimiter: return dict(CommonPrefixes=[dict(Prefix=p) for p in sorted({Prefix + k[len(Prefix):].split("/")[0] + "/" for k in keys})])
            after = [k for k in keys if ContinuationToken is None or k > ContinuationToken]   # paged by key, as a bucket pages
            page, more = after[:1500], len(after) > 1500
            return dict(Contents=[dict(Key=k) for k in page], IsTruncated=more, **(dict(NextContinuationToken=page[-1]) if more else {}))
        def delete_objects(self, Bucket, Delete):
            assert len(Delete["Objects"]) <= 1000; self.deletes += 1
            for o in Delete["Objects"]: self.objs.pop(o["Key"])
    # four complete builds, oldest first ("old" holds 2,500 files), and one a cancelled upload left without meta.json
    old = [f"builds/old/x{i}.bin" for i in range(2500)] + ["builds/old/meta.json"]
    old += [f"builds/{b}/{n}" for b in ("b1", "b2", "b3") for n in ("x.bin", "meta.json")] + ["builds/cut/x.bin"]
    b = Bucket(old)
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, "L0"))
    for name in ("meta.json", "L0/a.bin", "L0/b.bin"): open(os.path.join(d, name), "wb").write(b"x")
    assert U.upload(b, "bk", d, "new", threads=4) == 3 and b.puts[-1] == "builds/new/meta.json"   # meta.json last
    assert b.objs["builds/new/L0/a.bin"][:3] == (b"x", U.CACHE, "application/octet-stream")
    assert b.objs["builds/new/meta.json"][2] == "application/json"
    assert sorted(U.prune(b, "bk", current="new")) == ["b1", "cut", "old"]          # 2,500 files: 1,000 a request
    assert U.builds(b, "bk") == (["b2", "b3", "new"], []) and b.deletes == 6
    b.puts.clear()
    assert U.upload(b, "bk", d, "b2", threads=4) == 1 and b.puts == ["builds/b2/meta.json"]   # unchanged data: one write
    assert U.builds(b, "bk")[0] == ["b3", "new", "b2"]                                # and it counts as newest
    BM = B
    e = tempfile.mkdtemp(); os.makedirs(os.path.join(e, "L0"))
    for name in ("meta.json", "L0/a.bin", "L0/b.bin"): open(os.path.join(e, name), "wb").write(b"x")
    assert BM.data_id(d) == BM.data_id(e) and len(BM.data_id(d)) == 16
    open(os.path.join(e, "L0/b.bin"), "wb").write(b"y"); assert BM.data_id(d) != BM.data_id(e)


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
