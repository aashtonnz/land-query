"""Apply the row rules (overlays.finish_row) to published district results and rebuild what depends on them (T-82).

Usage: finish.py IN_DIR OUT_DIR. IN_DIR holds published results (units.parquet, provenance.json, blocks.json,
qa_summary.json, ...). OUT_DIR gets the same files with the rules applied, a fresh district.duckdb, the inverse
queries and measure checks rerun, finish.json recording what changed, and finish_note.txt saying what finishing could
not do (columns only a rebuild adds; values a newer rule would bring back). A fix that only changes how a parcel's own
values are published republishes in minutes this way; anything that needs new source data still needs a rebuild.
"""
import json, os, shutil, subprocess, sys
import duckdb, pandas as pd
import overlays as ov

HERE = os.path.dirname(os.path.abspath(__file__))


def finish_frame(df, int_cols):
    """(finished frame, {column: values changed}). Same rows, columns and order; integer columns stay whole."""
    dtypes = df.dtypes.to_dict()
    for c in int_cols: dtypes[c] = "Int64"   # pandas reads a whole-number column with gaps as decimals
    rows = [ov.finish_row({k: (None if (isinstance(v, float) and v != v) else v) for k, v in r.items()})
            for r in df.to_dict("records")]
    out = pd.DataFrame(rows, columns=df.columns, index=df.index)
    before = df.copy()
    for c, t in dtypes.items():
        for f in (out, before):
            try: f[c] = f[c].astype(t)
            except (TypeError, ValueError): pass
    changed = {c: int(((before[c].isna() != out[c].isna()) |
                       (before[c].notna() & out[c].notna() & (before[c].astype(str) != out[c].astype(str)))).sum())
               for c in df.columns}
    return out, {c: n for c, n in changed.items() if n}


def limits(out):
    """What finishing cannot do, as (columns only a rebuild adds, parcels whose building values a rebuild restores)."""
    sys.path.insert(0, os.path.join(HERE, "..", "service"))
    from catalogue import PENDING_COLUMNS
    missing = sorted(c for c in PENDING_COLUMNS if c not in out.columns)
    from councils import COUNCIL
    bcol = COUNCIL.RENAME_COLUMNS.get("building_2021_m2", "building_2021_m2")   # the council's name for it (T-97)
    restorable = int(((out["buildings_coverage_pct"] >= 99) & (out["coverage_pct"] >= 99) & out[bcol].isna()).sum())
    return missing, restorable


if __name__ == "__main__":
    import pyarrow.parquet as pq, pyarrow as pa
    IN, OUT = sys.argv[1], sys.argv[2]
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(IN):
        if f not in ("units.parquet", "district.duckdb", "inverse_queries.json", "measures_checks.json", "summary.md"):
            shutil.copy(os.path.join(IN, f), OUT)
    src = os.path.join(IN, "units.parquet")
    df = pd.read_parquet(src)
    out, changed = finish_frame(df, [f.name for f in pq.read_schema(src) if pa.types.is_integer(f.type)])
    print("values changed by column:", json.dumps(changed))

    db = duckdb.connect(os.path.join(OUT, "district.duckdb"))
    db.register("df_out", out)
    db.execute("CREATE OR REPLACE TABLE units AS SELECT * FROM df_out")
    prov = json.load(open(os.path.join(IN, "provenance.json")))
    db.execute("CREATE OR REPLACE TABLE provenance (source VARCHAR, json VARCHAR)")
    db.executemany("INSERT INTO provenance VALUES (?, ?)", [(k, json.dumps(v)) for k, v in prov.items()])
    db.execute(f"COPY units TO '{os.path.join(OUT, 'units.parquet')}' (FORMAT PARQUET)")
    db.close()

    missing, restorable = limits(out)
    note = ("Rules applied to published results; not a rebuild."
            + (f" Columns only a full rebuild adds, not yet present: {', '.join(missing)}." if missing else "")
            + (f" {restorable} parcels have building values a full rebuild would restore (finish.py only empties)."
               if restorable else ""))
    open(os.path.join(OUT, "finish_note.txt"), "w").write(note)
    print(note)
    run = os.path.join(IN, "RUN.txt")
    json.dump(dict(changed=changed, parcels=len(out), not_yet_in_results=missing, restorable_by_rebuild=restorable,
                   source_run=open(run).read().strip() if os.path.exists(run) else None),
              open(os.path.join(OUT, "finish.json"), "w"), indent=1)

    dbf = os.path.join(OUT, "district.duckdb")
    with open(os.path.join(OUT, "summary.md"), "w") as s:
        subprocess.run([sys.executable, os.path.join(HERE, "inverse_queries.py"), OUT, dbf], stdout=s, check=True, cwd=HERE)
    with open(os.path.join(OUT, "summary.md"), "a") as s:
        subprocess.run([sys.executable, os.path.join(HERE, "check_measures.py"), dbf, os.path.join(OUT, "measures_checks.json")],
                       stdout=s, check=True, cwd=HERE)
    print("finished:", len(out), "parcels")
