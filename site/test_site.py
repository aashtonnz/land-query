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


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
