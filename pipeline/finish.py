"""Apply the row rules (overlays.finish_row) to published district results and rebuild what depends on them (T-82).

Usage: finish.py IN_DIR OUT_DIR. IN_DIR holds published results (units.parquet, provenance.json, blocks.json,
qa_summary.json, ...). OUT_DIR gets the same files with the rules applied, a fresh district.duckdb, the inverse
queries and measure checks rerun, and finish.json recording what changed. A fix that only changes how a parcel's own
values are published republishes in minutes this way; anything that needs new source data still needs a rebuild.
"""
import json, os, shutil, subprocess, sys
import duckdb, pandas as pd
import overlays as ov

IN, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(IN):
    if f not in ("units.parquet", "district.duckdb", "inverse_queries.json", "measures_checks.json", "summary.md"):
        shutil.copy(os.path.join(IN, f), OUT)

import pyarrow.parquet as pq, pyarrow as pa
df = pd.read_parquet(os.path.join(IN, "units.parquet"))
dtypes = df.dtypes.to_dict()
# pandas reads a whole-number column with gaps as decimals: take integer columns from the file's own schema
for fld in pq.read_schema(os.path.join(IN, "units.parquet")):
    if pa.types.is_integer(fld.type): dtypes[fld.name] = "Int64"
rows = [ov.finish_row({k: (None if (isinstance(v, float) and v != v) else v) for k, v in r.items()})
        for r in df.to_dict("records")]
out = pd.DataFrame(rows, columns=df.columns)
for c, t in dtypes.items():  # whole numbers stay whole, with room for the values now empty (T-54)
    try: out[c] = out[c].astype(t)
    except (TypeError, ValueError): pass
before = df.copy()
for c, t in dtypes.items():
    try: before[c] = before[c].astype(t)
    except (TypeError, ValueError): pass
changed = {c: int(((before[c].isna() != out[c].isna()) | (before[c].notna() & out[c].notna() & (before[c].astype(str) != out[c].astype(str)))).sum())
           for c in df.columns}
changed = {c: n for c, n in changed.items() if n}
print("values changed by column:", json.dumps(changed))

db = duckdb.connect(os.path.join(OUT, "district.duckdb"))
db.register("df_out", out)
db.execute("CREATE OR REPLACE TABLE units AS SELECT * FROM df_out")
prov = json.load(open(os.path.join(IN, "provenance.json")))
db.execute("CREATE OR REPLACE TABLE provenance (source VARCHAR, json VARCHAR)")
db.executemany("INSERT INTO provenance VALUES (?, ?)", [(k, json.dumps(v)) for k, v in prov.items()])
db.execute(f"COPY units TO '{os.path.join(OUT, 'units.parquet')}' (FORMAT PARQUET)")
db.close()
json.dump(dict(changed=changed, parcels=len(out), source_run=open(os.path.join(IN, "RUN.txt")).read().strip()
               if os.path.exists(os.path.join(IN, "RUN.txt")) else None),
          open(os.path.join(OUT, "finish.json"), "w"), indent=1)

here = os.path.dirname(os.path.abspath(__file__))
dbf = os.path.join(OUT, "district.duckdb")
with open(os.path.join(OUT, "summary.md"), "w") as s:
    subprocess.run([sys.executable, os.path.join(here, "inverse_queries.py"), OUT, dbf], stdout=s, check=True, cwd=here)
with open(os.path.join(OUT, "summary.md"), "a") as s:
    subprocess.run([sys.executable, os.path.join(here, "check_measures.py"), dbf, os.path.join(OUT, "measures_checks.json")],
                   stdout=s, check=True, cwd=here)
print("finished:", len(out), "parcels")
