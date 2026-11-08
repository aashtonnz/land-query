"""Region-wide inverse queries over a compiled block or the merged district (T-33, T-21).

Each query is a plain filter over raw primitives (no scores). Every returned row carries the parcel id and
appellation, the values it was selected on, and the provenance of each source those values came from: URL and licence once per query, and the
sha256 and fetch time of the data the row's own block was compiled from. Usage: inverse_queries.py DIR [DBFILE] (default DIR/tile.duckdb).
Output: DIR/inverse_queries.json and a markdown summary on stdout.
"""
import json, os, sys
import duckdb
from provenance import row_sources, source_summary

D = sys.argv[1] if len(sys.argv) > 1 else "data"
DBF = sys.argv[2] if len(sys.argv) > 2 else os.path.join(D, "tile.duckdb")
db = duckdb.connect(DBF, read_only=True)
PROV = {k: json.loads(v) for k, v in db.execute("SELECT source, json FROM provenance").fetchall()}
from inverse_queries_defs import *   # noqa: F401,F403  (Q, Q_PORIRUA and their constants)
from councils import COUNCIL
Q = {"kapiti": Q, "porirua": Q_PORIRUA}[COUNCIL.NAME]


def prov(keys):
    return {k: source_summary(PROV[k]) for k in keys if k in PROV}

BLOCK_OF = dict(db.execute("SELECT unit_id, block_id FROM units").fetchall())

out = dict(database=os.path.basename(DBF), blocks=db.execute("SELECT count(DISTINCT block_id) FROM units").fetchone()[0], universe=db.execute(f"SELECT count(*) {BASE}").fetchone()[0],
           queries=[])
for q in Q:
    res = db.execute(q["sql"]); cols = [c[0] for c in res.description]
    rows = [dict(zip(cols, r)) for r in res.fetchall()]
    for r in rows:  # each row: the sha256 and fetch time of the data its own block was compiled from
        r["block_id"] = BLOCK_OF.get(r["unit_id"]); r["sources"] = row_sources(PROV, q["sources"], r["block_id"])
    out["queries"].append(dict(id=q["id"], name=q["name"], question=q["question"], sql=" ".join(q["sql"].split()),
                               count=len(rows), provenance=prov(q["sources"]), rows=rows))
    print(f"| {q['id']} | {q['name']} | {len(rows)} |")
json.dump(out, open(os.path.join(D, "inverse_queries.json"), "w"), indent=1, default=str)
missing = sum(1 for q, qq in zip(Q, out["queries"]) for r in qq["rows"] for k in q["sources"] if k in PROV and k not in r["sources"])
print("rows missing a source's sha256 or fetch time:", missing)
no_url = sum(1 for qq in out["queries"] for k, v in qq["provenance"].items() if not v.get("url") or not v.get("licence"))
print("sources without a URL or licence:", no_url)
print("universe:", out["universe"], "parcels wholly in tile")
