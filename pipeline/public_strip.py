"""Remove what public mode withholds from a results folder before it is published (D-15, D-17, D-24, T-106).

Usage: public_strip.py DIR. In every .parquet file under DIR the columns `titles` (LINZ title references, a direct key
to owner records) and `title_types` (a Life Estate says a living person holds an interest) are dropped; in every .json
file, the same keys are dropped from each row (any object holding `unit_id` or `parcel_id`). The title count stays.
Fails if either column is still present afterwards.
"""
import json, os, sys
import pyarrow.parquet as pq

WITHHELD = ("titles", "title_types")


def strip_json(x):
    if isinstance(x, dict):
        is_row = "unit_id" in x or "parcel_id" in x
        return {k: strip_json(v) for k, v in x.items() if not (is_row and k in WITHHELD)}
    if isinstance(x, list): return [strip_json(v) for v in x]
    return x


def strip(d):
    done = []
    for root, _, files in os.walk(d):
        for f in files:
            p = os.path.join(root, f)
            if f.endswith(".parquet"):
                t = pq.read_table(p); drop = [c for c in WITHHELD if c in t.column_names]
                if drop: pq.write_table(t.drop(drop).replace_schema_metadata(None), p, compression="zstd"); done.append((p, drop))   # stale pandas metadata too
                assert not set(WITHHELD) & set(pq.read_schema(p).names), p
            elif f.endswith(".json"):
                j = json.load(open(p)); s = strip_json(j)
                if s != j: json.dump(s, open(p, "w"), indent=1, ensure_ascii=False); done.append((p, "rows"))
    return done


if __name__ == "__main__":
    for p, what in strip(sys.argv[1]): print("stripped", what, "from", p)
