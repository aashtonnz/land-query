"""D8 overland flow that drains every cell (T-42).

Priority-flood with epsilon (Barnes, Lehman and Mulla 2014) raises each depression and flat just enough that every
valid cell has a strictly lower neighbour on a path to an outlet (a valid cell on the raster edge or next to no
data). Each cell then drains to its steepest-descent neighbour on the raised surface. This replaces pysheds, whose
resolve_flats left some valley-floor cells with no flow direction, stopping rivers mid-valley.
"""
import heapq, math
import numpy as np
from numba import njit

DR = np.array([-1, -1, 0, 1, 1, 1, 0, -1], np.int64)   # N, NE, E, SE, S, SW, W, NW
DC = np.array([0, 1, 1, 1, 0, -1, -1, -1], np.int64)
DIST = np.array([1, math.sqrt(2), 1, math.sqrt(2), 1, math.sqrt(2), 1, math.sqrt(2)])


@njit(cache=True)
def _fill(z, ok):
    H, W = z.shape
    zf = np.where(ok, z.astype(np.float64), np.nan)
    done = ~ok
    heap = [(0.0, np.int64(0))]; heap.pop()
    for r in range(H):
        for c in range(W):
            if not ok[r, c]: continue
            seed = r == 0 or c == 0 or r == H - 1 or c == W - 1
            if not seed:
                for k in range(8):
                    if not ok[r + DR[k], c + DC[k]]: seed = True; break
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
def _receivers(zf, ok):
    """Index of the steepest-descent neighbour, or -1 for an outlet; and the direction code 0-7 (-1 for none)."""
    H, W = zf.shape
    rec = np.full(H * W, -1, np.int64); dirn = np.full((H, W), -1, np.int8)
    for r in range(H):
        for c in range(W):
            if not ok[r, c]: continue
            best, bk = 0.0, -1
            for k in range(8):
                rn, cn = r + DR[k], c + DC[k]
                if rn < 0 or cn < 0 or rn >= H or cn >= W or not ok[rn, cn]: continue
                s = (zf[r, c] - zf[rn, cn]) / DIST[k]
                if s > best: best, bk = s, k
            if bk >= 0:
                rec[r * W + c] = (r + DR[bk]) * W + c + DC[bk]; dirn[r, c] = bk
    return rec, dirn


@njit(cache=True)
def _accumulate(order, rec, w):
    acc = w.copy()
    for i in order:
        j = rec[i]
        if j >= 0: acc[j] += acc[i]
    return acc


def flow_routing(dem, transform, inflow=None):
    """Upslope area (m², counting the cell itself), truncated flag, and step length (m) for each cell.

    truncated is True where the cell's upslope area includes an inflow cell, where flow from beyond the raster may
    enter (default: cells on the raster edge or next to no data). NaN cells are no data and act as outlets."""
    ok = np.isfinite(dem)
    zf = _fill(np.ascontiguousarray(dem, dtype=np.float32), ok)
    rec, dirn = _receivers(zf, ok)
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
