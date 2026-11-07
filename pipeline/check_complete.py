"""Refuse to publish a partial district run (T-48).

Usage: check_complete.py PLANNED_JSON BLOCKS_DIR ONLY DISTRICT_BLOCKS. Exits non-zero, so the push step is skipped, when
the run was limited with the `only` input, when it planned fewer blocks than the district has, or when any planned
block's results are missing.
"""
import glob, json, os, sys


def problems(planned, present, only, district_blocks):
    out = []
    if only.strip(): out.append(f"run limited to blocks {only!r}: not published as the district")
    if len(planned) != district_blocks: out.append(f"planned {len(planned)} blocks of the district's {district_blocks}")
    missing = sorted(f"{b['xmin']}_{b['ymin']}" for b in planned if f"{b['xmin']}_{b['ymin']}" not in present)
    if missing: out.append(f"{len(missing)} planned blocks have no results: {', '.join(missing[:10])}")
    return out


if __name__ == "__main__":
    planned = json.loads(sys.argv[1])
    present = {os.path.basename(d).removeprefix("block-") for d in glob.glob(os.path.join(sys.argv[2], "block-*"))
               if os.path.exists(os.path.join(d, "units.parquet"))}
    p = problems(planned, present, sys.argv[3], int(sys.argv[4]))
    for x in p: print("NOT PUBLISHED:", x)
    sys.exit(1 if p else 0)
