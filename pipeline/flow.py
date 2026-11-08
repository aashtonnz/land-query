"""D8 overland flow that drains every cell (T-42).

Priority-flood with epsilon (Barnes, Lehman and Mulla 2014) raises each depression and flat just enough that every
valid cell has a strictly lower neighbour on a path to an outlet (a valid cell on the raster edge, or next to no data
that lies no higher than it, such as the sea). A cell next to the sea drains into it when that is its steepest drop
(T-47: before, such cells only drained sideways along the beach). Each cell then drains to its steepest-descent neighbour on the raised surface. This replaces pysheds, whose
resolve_flats left some valley-floor cells with no flow direction, stopping rivers mid-valley.
"""
import heapq, math
import numpy as np
from numba import njit

DR = np.array([-1, -1, 0, 1, 1, 1, 0, -1], np.int64)   # N, NE, E, SE, S, SW, W, NW
DC = np.array([0, 1, 1, 1, 0, -1, -1, -1], np.int64)
SEA_M = -1000.0  # the elevation given to sea cells: below any land
DIST = np.array([1, math.sqrt(2), 1, math.sqrt(2), 1, math.sqrt(2), 1, math.sqrt(2)])


@njit(cache=True)
def _fill(z, ok, outside):
    H, W = z.shape
    zf = np.where(ok, z.astype(np.float64), np.nan)
    done = ~ok
    heap = [(0.0, np.int64(0))]; heap.pop()
    for r in range(H):
        for c in range(W):
            if not ok[r, c]: continue
            # an outlet: on the raster edge, or next to no data that lies no higher than the cell (the sea, say)
            seed = r == 0 or c == 0 or r == H - 1 or c == W - 1
            if not seed:
                for k in range(8):
                    rn, cn = r + DR[k], c + DC[k]
                    if not ok[rn, cn] and outside[rn, cn] <= zf[r, c]: seed = True; break
            if seed:
                heapq.heappush(heap, (zf[r, c], np.int64(r * W + c))); done[r, c] = True
    while heap:
        e, i = heapq.heappop(heap)
        r, c = i // W, i % W
        for k in range(8):
            rn, cn = r + DR[k], c + DC[k]
            if rn < 0 or cn < 0 or rn >= H or cn >= W or done[rn, cn]: continue
            done[rn, cn] = True
            if zf[rn, cn] <= e: zf[rn, cn] = np.nextafter(e, np.inf)
            heapq.heappush(heap, (zf[rn, cn], np.int64(rn * W + cn)))
    return zf


@njit(cache=True)
def _receivers(zf, ok, outside):
    """Index of the steepest-descent neighbour, or -1 where the cell drains out of the raster (into no data, or off
    an edge with no lower neighbour); and the direction code 0-7 of that step (-1 for none)."""
    H, W = zf.shape
    rec = np.full(H * W, -1, np.int64); dirn = np.full((H, W), -1, np.int8)
    for r in range(H):
        for c in range(W):
            if not ok[r, c]: continue
            best, bk, out = 0.0, -1, False
            for k in range(8):
                rn, cn = r + DR[k], c + DC[k]
                if rn < 0 or cn < 0 or rn >= H or cn >= W: continue
                if ok[rn, cn]: s = (zf[r, c] - zf[rn, cn]) / DIST[k]
                else: s = (zf[r, c] - outside[rn, cn]) / DIST[k]   # into the sea, or onto unsurveyed lower ground
                if s > best: best, bk, out = s, k, not ok[rn, cn]
            if bk >= 0:
                dirn[r, c] = bk
                if not out: rec[r * W + c] = (r + DR[bk]) * W + c + DC[bk]
    return rec, dirn


@njit(cache=True)
def _accumulate(order, rec, w):
    acc = w.copy()
    for i in order:
        j = rec[i]
        if j >= 0: acc[j] += acc[i]
    return acc


def flow_routing(dem, transform, inflow=None, outside=None):
    """Upslope area (m², counting the cell itself), truncated flag, and step length (m) for each cell.

    NaN cells are no data. outside gives their elevation (known ground where the survey has a gap); where it is NaN or
    not given, the cell is sea, below any land (SEA_M), so coastal land below 0 m still drains into it (T-59). A cell drains into no data when that is its steepest drop, and the flow
    leaves the raster there. truncated is True where the cell's upslope area includes an inflow cell, where flow from
    beyond the raster may enter (default: cells on the raster edge or next to no data)."""
    ok = np.isfinite(dem)
    out = np.full(dem.shape, SEA_M) if outside is None else np.where(np.isfinite(outside), outside, SEA_M).astype(np.float64)
    zf = _fill(np.ascontiguousarray(dem, dtype=np.float32), ok, out)
    rec, dirn = _receivers(zf, ok, out)
    del out
    order = np.argsort(-np.nan_to_num(zf, nan=-np.inf).ravel(), kind="stable")
    del zf
    order = order[ok.ravel()[order]]
    acc = _accumulate(order, rec, ok.ravel().astype(np.float64)).reshape(dem.shape).astype(np.float32)
    if inflow is None:
        from scipy.ndimage import binary_dilation
        inflow = np.zeros(dem.shape, bool); inflow[0, :] = inflow[-1, :] = inflow[:, 0] = inflow[:, -1] = True
        inflow |= binary_dilation(~ok)
    reach = _accumulate(order, rec, (inflow & ok).ravel().astype(np.float64)).reshape(dem.shape) > 0
    del order, rec
    cell = abs(transform.a)
    step = np.where(dirn % 2 == 1, cell * math.sqrt(2), cell).astype(np.float32)
    acc[~ok] = np.nan; step[~ok] = np.nan; step[dirn < 0] = 0
    return acc * abs(transform.a * transform.e), reach & ok, step
