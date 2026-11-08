"""Copy the published results of the council named by COUNCIL (default kapiti) from its `<council>-results` branch
into a folder for the server (T-87): `kapiti-results` or `porirua-results`.

Usage: COUNCIL=porirua python3 fetch_results.py [OUT_DIR]   (default: results). Needs a clone of the repository.
"""
import os, subprocess, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "results"
BRANCH = os.environ.get("COUNCIL", "kapiti") + "-results"
os.makedirs(OUT, exist_ok=True)
subprocess.run(["git", "fetch", "-q", "origin", BRANCH], check=True)
for f in ("units.parquet", "provenance.json", "inverse_queries.json", "RUN.txt", "qa_summary.json"):
    r = subprocess.run(["git", "show", f"origin/{BRANCH}:results/{f}"], capture_output=True)
    if r.returncode == 0: open(os.path.join(OUT, f), "wb").write(r.stdout); print("copied", f)
    else: print("not published yet:", f)
