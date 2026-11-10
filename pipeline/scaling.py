"""How the national index's work grows with the data (T-102): time each stage on the same kind of area at 1x, 2x and
4x the size, fit the growth (the slope of log time against log parcels: 1 is linear, 2 quadratic), and predict the
largest tile. Today's case: the water share merged the coast around every parcel, so its cost grew with parcels x
coast detail; fine in Wellington, hours in Auckland. A slope well above 1 shows that before a national run.

synthetic(n) makes a made-up suburb of about n parcels on a wiggly coast, in which every quantity grows with the area
(parcels, roads, buildings, addresses, coast vertices), as it does in real towns. measure() times each stage there.

Usage: python3 scaling.py [BASE_PARCELS]   prints each stage's slope and the time predicted for the densest tile
(MAX_TILE_PARCELS); test_national.py runs a small version on every change and fails if a stage grows faster than
MAX_SLOPE.
"""
import math, sys, time
import numpy as np
from shapely.geometry import Polygon, box, Point
import national_index as N

MAX_SLOPE = 1.3              # a stage growing faster than parcels^1.3 fails the test
MAX_TILE_PARCELS = 400_000   # about the most parcels one 40 km tile holds (central Auckland), with margin


def synthetic(n, seed=0):
    """(parcels, roads, buildings, addresses, coast, land, water, neighbours) for about n parcels: 20 m lots in
    blocks of 4 x 10 with 10 m roads, on land whose shore is a wiggly line (a vertex every 0.5 m, as detailed as a real harbour coast per km of tile) across the middle."""
    rng = np.random.default_rng(seed)
    side = int(math.ceil(math.sqrt(n * 600)))              # about 600 m² of ground per parcel, roads included
    yshore = side * 0.75
    xs = np.arange(0, side + 0.5, 0.5)
    ys = yshore + 15 * np.sin(xs / 37.0) + 6 * np.sin(xs / 7.3) + rng.normal(0, 1.5, len(xs))
    land = Polygon([(-50, -50)] + list(zip(xs, ys)) + [(side + 50, -50)])
    parcels, roads, buildings, addresses, neighbours = [], [], [], [], []
    pid = 0
    for bx in range(0, side, 50):                          # blocks 40 m wide (2 lots) and 200 m tall (10 lots), 10 m roads
        roads.append((box(bx + 40, 0, bx + 50, side), dict(parcel_intent="Road")))
        for by in range(0, side, 210):
            roads.append((box(bx, by + 200, bx + 40, by + 210), dict(parcel_intent="Road")))
            for i in range(2):
                for j in range(10):
                    g = box(bx + 20 * i, by + 20 * j, bx + 20 * i + 20, by + 20 * j + 20)
                    if g.bounds[1] > yshore + 40: continue   # lots only up to just past the shore
                    pid += 1; p = dict(id=pid, parcel_intent="DCDB", titles=f"T{pid}")
                    parcels.append((g, p, g.representative_point())); neighbours.append((g, p))
                    c = g.centroid
                    buildings.append((box(c.x - 5, c.y - 5, c.x + 5, c.y + 5), dict(building_id=pid, use_="House")))
                    addresses.append((Point(c.x, c.y), dict(address_id=pid, full_address=f"{pid} Street", address_number=pid)))
    coast = [(land.exterior, dict(id=1))]
    water = [(box(side * 0.3, side * 0.2, side * 0.3 + 60, side * 0.2 + 60), dict(t50_fid=1))]   # one small lake
    return parcels, roads, buildings, addresses, coast, [(land, dict(id=1))], water, neighbours


def measure(n, repeats=2):
    """{stage: seconds} for about n parcels (the quicker of `repeats` runs), and the parcel count."""
    parcels, roads, buildings, addresses, coast, land, water, nb = synthetic(n)
    stages = dict(
        vector=lambda: N.vector_columns(parcels, roads, {}, buildings, addresses, coast, (), nb),
        water=lambda: N.water_shares(parcels, water, land))
    out = {}
    for name, f in stages.items():
        best = math.inf
        for _ in range(repeats):
            t0 = time.perf_counter(); f(); best = min(best, time.perf_counter() - t0)
        out[name] = best
    return out, len(parcels)


def slopes(base=1000, steps=3, repeats=2):
    """{stage: (slope, seconds at the largest size, sizes)} from runs at base, 2x base, 4x base ..."""
    runs = [measure(base * 2 ** k, repeats) for k in range(steps)]
    ns = np.log([n for _, n in runs]); out = {}
    for stage in runs[0][0]:
        ts = np.log([max(r[stage], 1e-4) for r, _ in runs])
        out[stage] = (float(np.polyfit(ns, ts, 1)[0]), runs[-1][0][stage], [n for _, n in runs])
    return out


if __name__ == "__main__":
    base = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    for stage, (k, t, ns) in slopes(base).items():
        pred = t * (MAX_TILE_PARCELS / ns[-1]) ** k
        print(f"{stage:8s} slope {k:.2f} ({ns[-1]:,} parcels: {t:.2f} s) -> about {pred / 60:.1f} min for {MAX_TILE_PARCELS:,} parcels"
              + ("  TOO STEEP" if k > MAX_SLOPE else ""))
