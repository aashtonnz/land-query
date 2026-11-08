"""Refuse to publish a partial district run (T-48).

Usage: check_complete.py PLANNED_JSON BLOCKS_DIR ONLY DISTRICT_BLOCKS. Exits non-zero, so the push step is skipped, when
the run was limited with the `only` input, when it planned fewer blocks than the district has, or when any planned
block's results are missing.
"""
import glob, json, os, sys


def problems(planned, present, only, district_blocks, failed=None, flow_shas=None):
    """failed: {block id: [source keys that failed]}; flow_shas: {block id: district-flow sha256}, from each block's
    provenance (T-59, T-62: a patch run must not mix district-flow grids)."""
    out = []
    shas = set((flow_shas or {}).values())
    if None in shas: out.append(f"{sum(1 for v in flow_shas.values() if not v)} blocks have no district-flow record")  # T-65
    shas.discard(None)
    if len(shas) > 1: out.append(f"blocks used {len(shas)} different district-flow grids")
    bad = {b: f for b, f in (failed or {}).items() if f}
    if bad: out.append(f"{len(bad)} blocks have failed sources, which would publish as empty or 0: " + "; ".join(f"{b}: {', '.join(f)}" for b, f in sorted(bad.items())[:10]))
    if only.strip(): out.append(f"run limited to blocks {only!r}: not published as the district")
    if len(planned) != district_blocks: out.append(f"planned {len(planned)} blocks of the district's {district_blocks}")
    missing = sorted(f"{b['xmin']}_{b['ymin']}" for b in planned if f"{b['xmin']}_{b['ymin']}" not in present)
    if missing: out.append(f"{len(missing)} planned blocks have no results: {', '.join(missing[:10])}")
    return out


def read_blocks(blocks_dir):
    """(blocks with results, {block: failed sources}, {block: district-flow sha256 or None}) from the block folders."""
    present = {os.path.basename(d).removeprefix("block-") for d in glob.glob(os.path.join(blocks_dir, "block-*"))
               if os.path.exists(os.path.join(d, "units.parquet"))}
    failed, flow_shas = {}, {}
    for d in glob.glob(os.path.join(blocks_dir, "block-*")):
        pp = os.path.join(d, "provenance.json"); bid = os.path.basename(d).removeprefix("block-")
        if not os.path.exists(pp):  # results without provenance cannot be checked: refuse them (T-70)
            failed[bid], flow_shas[bid] = ["provenance.json missing"], None; continue
        src = json.load(open(pp))["sources"]
        failed[bid] = sorted(k for k, v in src.items() if not v.get("ok", True) and not v.get("no_coverage"))
        flow_shas[bid] = src.get("district_flow", {}).get("sha256")
    return present, failed, flow_shas


if __name__ == "__main__":
    planned = json.loads(sys.argv[1])
    present, failed, flow_shas = read_blocks(sys.argv[2])
    p = problems(planned, present, sys.argv[3], int(sys.argv[4]), failed, flow_shas)
    for x in p: print("NOT PUBLISHED:", x)
    sys.exit(1 if p else 0)
