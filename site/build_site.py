"""Build the project page (an explorer of both councils' published results) as one HTML file (T-98).

Usage: python3 site/build_site.py OUT.html. Reads the published results from the `kapiti-results` and
`porirua-results` branches, keeps only columns served in public mode, and fills site/template.html. It also writes
national-1.json and national-2.json beside OUT.html from the `national-pilot` branch (T-100): the Greater
Wellington parcels outside the two councils. Publish both with the page as supporting files. The output is
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


data = {"fields": COLS + KAPITI_ONLY + ["c"], "rows": [], "stats": {}}   # rows of both councils
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
# the national index pilot (T-100): Greater Wellington parcels outside the two councils' results, as a separate data
# file the page loads after it opens (it is too large to inline). LINZ data only, all CC BY 4.0; title types are left
# out as in public mode (D-17)
have = {r[0] for r in data["rows"]}
nd = results("national-pilot")
nf = os.path.join(nd, "index.parquet")
q = duckdb.sql(f"""SELECT parcel_id, appellation, parcel_intent, round(rep_x)::BIGINT, round(rep_y)::BIGINT,
        round(area_m2)::BIGINT, round(ground_mean_m, 1), round(upslope_area_max_m2)::BIGINT, title_count,
        round(building_cover_pct)::BIGINT, address, territorial_authority FROM '{nf}' ORDER BY parcel_id""").fetchall()
# the council rows get their LINZ address too, so the plan can be searched by address everywhere; their extra fields
# follow the page's order (building_cover_pct, street, place, territorial_authority)
by_id = {r[0]: r[10] for r in q}
for row in data["rows"]:
    a = by_id.get(row[0]); a = a.split(", ", 1) if a else None
    row += [None, a[0] if a else None, (a[1] if len(a) > 1 else "") if a else None, None]
q = [r for r in q if r[0] not in have]
cl = lambda v: None if v is None or (isinstance(v, float) and v != v) else v


def coded(vals):
    """(sorted distinct values, each value's index, -1 for none): short repeated text sent once."""
    u = sorted({v for v in vals if v is not None}); ix = {v: k for k, v in enumerate(u)}
    return dict(values=u, codes=[ix[v] if v is not None else -1 for v in vals])


# two files, each under the 16 MB limit for a published file: positions and numbers (the plan), then names (search)
core = dict(unit_id=[r[0] for r in q], rep_x=[r[3] for r in q], rep_y=[r[4] for r in q], area_m2=[cl(r[5]) for r in q],
            ground_mean_m=[cl(r[6]) for r in q], catchment_area_max_m2=[cl(r[7]) for r in q],
            title_count=[cl(r[8]) for r in q], building_cover_pct=[cl(r[9]) for r in q],
            parcel_intent=coded([r[2] for r in q]), territorial_authority=coded([r[11] for r in q]))
addr = [r[10].split(", ", 1) if r[10] else None for r in q]
text = dict(appellation=[r[1] for r in q], street=[a[0] if a else None for a in addr],
            place=coded([(a[1] if len(a) > 1 else "") if a else None for a in addr]))
outdir = os.path.dirname(os.path.abspath(OUT))
for name, obj in (("national-1.json", core), ("national-2.json", text)):
    pth = os.path.join(outdir, name)
    json.dump(obj, open(pth, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    size = os.path.getsize(pth) / 1e6
    assert size < 15, f"{name} is {size:.1f} MB, over the limit for a published file"
    print("wrote", pth, round(size, 1), "MB")
n_all, nmed = duckdb.sql(f"SELECT count(*), round(median(ground_mean_m), 1) FROM '{nf}'").fetchall()[0]
data["stats"]["n"] = dict(parcels=n_all, extra=len(q), median_ground=nmed,
                          run="national index pilot, built from " + open(os.path.join(nd, "BUILT_FROM.txt")).read().strip())
html = open(os.path.join(ROOT, "site", "template.html"), encoding="utf-8").read()
open(OUT, "w", encoding="utf-8").write(html.replace("__DATA__", json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")))
print("wrote", OUT, len(data["rows"]), "parcels")
