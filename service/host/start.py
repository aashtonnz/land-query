"""Fetch the newest published national index, prepare it for the service, and serve it over HTTP (T-26).

LANDQ_REPO (default aashtonnz/land-query) names the repository whose national-* releases are read; LANDQ_RESULTS is
where the prepared results go. A release is downloaded only if it is not there already, so a restart is quick.
"""
import json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
REPO = os.environ.get("LANDQ_REPO", "aashtonnz/land-query")
OUT = os.environ.get("LANDQ_RESULTS", "/data/results")


def newest_release():
    """The newest release whose tag starts national-, with its assets {name: download url}."""
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/releases?per_page=100", headers={"Accept": "application/vnd.github+json"})
    for r in json.load(urllib.request.urlopen(req, timeout=60)):
        if r["tag_name"].startswith("national-") and not r.get("draft"):
            return r["tag_name"], {a["name"]: a["browser_download_url"] for a in r["assets"]}
    raise SystemExit(f"no national-* release in {REPO}")


def main():
    tag, assets = newest_release()
    if open(os.path.join(OUT, "TAG.txt")).read().strip() == tag if os.path.exists(os.path.join(OUT, "TAG.txt")) else False:
        print("prepared already:", tag)
    else:
        raw = os.path.join(os.path.dirname(OUT), "release"); os.makedirs(raw, exist_ok=True)
        for name in ("index.parquet", "provenance.json", "run.json"):
            print("fetching", tag, name, flush=True)
            urllib.request.urlretrieve(assets[name], os.path.join(raw, name))
        from prepare_national import prepare
        prepare(raw, OUT)
        open(os.path.join(OUT, "TAG.txt"), "w").write(tag)
    import runpy
    sys.argv = [os.path.join(os.path.dirname(HERE), "server.py")]
    runpy.run_path(sys.argv[0], run_name="__main__")


if __name__ == "__main__":
    main()
