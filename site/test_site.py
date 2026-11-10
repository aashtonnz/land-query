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


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"): f(); print("ok", name)
