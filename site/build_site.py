"""Build the project page (an explorer of both councils' published results) as one HTML file (T-98).

Usage: python3 site/build_site.py OUT.html. Reads the published results from the `kapiti-results` and
`porirua-results` branches, keeps only columns served in public mode, and fills site/template.html. The output is
about 6 MB (the data is inlined), so it is not committed; it is published as a private Claude page.
"""
import json, math, os, subprocess, sys, tempfile
import duckdb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else "land-query-site.html"
COLS = ["unit_id", "appellation", "parcel_intent", "rep_x", "rep_y", "area_m2", "ground_mean_m", "slope_p90_deg",
        "lidar_coverage_pct", "flow_path_m", "catchment_area_max_m2", "title_count", "easements_n"]
KAPITI_ONLY = ["ww_pipe_dist_m", "ww_pipe_year", "ww_pipe_condition_grade", "ws_pipe_dist_m"]   # KCDC's ✅ three waters


def results(branch):
    d = tempfile.mkdtemp()
    subprocess.run(["git", "fetch", "-q", "origin", branch], cwd=ROOT, check=True)
    tar = subprocess.run(["git", "archive", f"origin/{branch}", "results"], cwd=ROOT, check=True, capture_output=True).stdout
    subprocess.run(["tar", "-x", "-C", d], input=tar, check=True)
    return os.path.join(d, "results")


def public_columns(council, d):
    """Columns the service serves in public mode for this council (only those go on the page)."""
    code = f"import sys; sys.path.insert(0, 'service'); from landquery import LandQuery; print(' '.join(LandQuery({d!r}, 'public').columns))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=dict(os.environ, COUNCIL=council), check=True,
                         capture_output=True, text=True).stdout
    return set(out.split())


def num(v):
    if v is None or (isinstance(v, float) and math.isnan(v)): return None
    if isinstance(v, float): return round(v, 1) if abs(v) < 1e5 else round(v)
    return v


data = {"fields": COLS + KAPITI_ONLY + ["c"], "rows": [], "stats": {}}
for c, council, branch, extra in [("k", "kapiti", "kapiti-results", KAPITI_ONLY), ("p", "porirua", "porirua-results", [])]:
    d = results(branch)
    pub = public_columns(council, d)
    cols = [x for x in COLS + extra if x in pub]
    assert set(COLS) <= pub | {"rep_x", "rep_y"}, sorted(set(COLS) - pub)
    f = os.path.join(d, "units.parquet")
    for r in duckdb.sql(f"SELECT {', '.join(cols)} FROM '{f}' ORDER BY unit_id").fetchall():
        row = dict(zip(cols, r))
        data["rows"].append([num(row.get(k)) for k in COLS + KAPITI_ONLY] + [c])
    n, lid, med = duckdb.sql(f"SELECT count(*), count(ground_mean_m), round(median(ground_mean_m), 1) FROM '{f}'").fetchall()[0]
    data["stats"][c] = dict(parcels=n, with_lidar=lid, median_ground=med, run=open(os.path.join(d, "RUN.txt")).read().strip())
html = open(os.path.join(ROOT, "site", "template.html"), encoding="utf-8").read()
open(OUT, "w", encoding="utf-8").write(html.replace("__DATA__", json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")))
print("wrote", OUT, len(data["rows"]), "parcels")
