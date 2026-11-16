"""Compare a new national build with the last published one (T-102, D-27): national_compare.py OLD_INDEX NEW_INDEX.

The monthly build publishes itself only if nothing has moved more than LINZ's month of changes can explain; anything
else waits for a person. Prints one line per check and exits 1 if any fails. The checks:

- parcels: the count changes by no more than -1% / +3% (New Zealand adds well under 1% a month);
- columns: no column is lost;
- unknowns: no column's share of empty values grows by more than 1 point;
- values: for parcels in both builds, no column changes materially on more than 5% of them (a new LiDAR survey for a
  whole region can pass this; one that does not is looked at by a person);
- districts: no district's parcel count changes by more than 5% (50 parcels for small ones).
"""
import sys
import numpy as np
import pandas as pd

COUNT_RANGE = (-0.01, 0.03)
UNKNOWN_POINTS = 1.0
CHANGED_SHARE = 0.05
DISTRICT_SHARE, DISTRICT_MIN = 0.05, 50
SKIP = {"parcel_id", "geometry_wkb", "rep_x", "rep_y"}   # identity and shape: compared through the other columns


def changed(a, b):
    """True where two values differ materially: numbers by more than 1% and 0.5 units, others when not equal."""
    if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b) and not pd.api.types.is_bool_dtype(a):
        a, b = a.astype(float), b.astype(float)
        both = a.notna() & b.notna()
        d = (a - b).abs()
        return (a.isna() != b.isna()) | (both & (d > 0.5) & (d > 0.01 * np.maximum(a.abs(), b.abs())))
    return (a.isna() != b.isna()) | (a.notna() & b.notna() & (a.astype(str) != b.astype(str)))


def compare(old, new):
    """[(check, passed, detail)]."""
    out = []
    g = len(new) / len(old) - 1
    out.append(("parcels", COUNT_RANGE[0] <= g <= COUNT_RANGE[1], f"{len(old):,} -> {len(new):,} ({g:+.2%})"))
    lost = sorted(set(old.columns) - set(new.columns))
    out.append(("columns", not lost, f"lost {lost}" if lost else f"{len(new.columns)} columns, none lost"))
    cols = [c for c in old.columns if c in new.columns and c not in SKIP]
    for c in cols:
        up = (new[c].isna().mean() - old[c].isna().mean()) * 100
        if up > UNKNOWN_POINTS: out.append((f"unknowns {c}", False, f"empty share up {up:.1f} points"))
    j = old[["parcel_id"] + cols].merge(new[["parcel_id"] + cols], on="parcel_id", suffixes=("_o", "_n"))
    for c in cols:
        s = float(changed(j[c + "_o"], j[c + "_n"]).mean()) if len(j) else 0.0
        if s > CHANGED_SHARE: out.append((f"values {c}", False, f"changed on {s:.1%} of {len(j):,} parcels in both"))
    out.append(("unknowns and values", True, f"{len(cols)} columns checked on {len(j):,} parcels in both"))
    if "territorial_authority" in cols:
        a, b = old.territorial_authority.value_counts(), new.territorial_authority.value_counts()
        bad = [f"{d}: {int(a.get(d, 0)):,} -> {int(b.get(d, 0)):,}" for d in sorted(set(a.index) | set(b.index))
               if abs(int(b.get(d, 0)) - int(a.get(d, 0))) > max(DISTRICT_MIN, DISTRICT_SHARE * int(a.get(d, 0)))]
        out.append(("districts", not bad, "; ".join(bad) if bad else f"{len(b)} districts within {DISTRICT_SHARE:.0%}"))
    return out


if __name__ == "__main__":
    res = compare(pd.read_parquet(sys.argv[1]), pd.read_parquet(sys.argv[2]))
    for name, ok, detail in res: print(("ok    " if ok else "FAILED"), name + ":", detail)
    sys.exit(0 if all(ok for _, ok, _ in res) else 1)
