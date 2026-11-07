"""Copy the published district results from the `kapiti-results` branch into a folder for the server.

Usage: python3 fetch_results.py [OUT_DIR]   (default: results). Needs a clone of the repository with the branch fetched.
"""
import os, subprocess, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "results"
os.makedirs(OUT, exist_ok=True)
subprocess.run(["git", "fetch", "-q", "origin", "kapiti-results"], check=True)
for f in ("units.parquet", "provenance.json", "inverse_queries.json", "RUN.txt", "qa_summary.json"):
    r = subprocess.run(["git", "show", f"origin/kapiti-results:results/{f}"], capture_output=True)
    if r.returncode == 0: open(os.path.join(OUT, f), "wb").write(r.stdout); print("copied", f)
    else: print("not published yet:", f)
