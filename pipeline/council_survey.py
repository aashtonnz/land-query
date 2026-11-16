"""Which New Zealand councils publish zoning and hazard layers with a licence stated on the dataset (T-35, T-38).

Usage: council_survey.py OUT_DIR. Searches ArcGIS Online's public catalogue (where most councils publish their maps)
for feature layers inside New Zealand on each TOPIC, reads each item's licence text, and writes:
- OUT_DIR/council_layers.json: every item found (topic, title, owner organisation, url, licence text, licence class);
- OUT_DIR/council_survey.md: per organisation, the topics it publishes and whether each has a dataset licence.

A "dataset licence" is a Creative Commons licence (or another open licence) written on the item itself, which this
project accepts without writing to the council (SOURCES.md, "Licence basis"); anything else needs the council to
confirm (T-35). Needs www.arcgis.com, which GitHub's runners reach. Makes about 200 requests, a second apart.
"""
import json, os, re, sys, time
import requests

API = "https://www.arcgis.com/sharing/rest"
NZ = "165,-48,179,-34"   # lon/lat box around New Zealand's main islands
TOPICS = {
    "zoning": ['"district plan" zone', "district plan zones", "zoning", "unitary plan zone", "planning zones"],
    "flood": ["flood hazard", "flood plain", "flood extent", "flooding", "overland flow"],
    "coastal": ["coastal inundation", "coastal erosion", "sea level rise", "tsunami evacuation"],
    "land": ["liquefaction", "landslide", "slope hazard", "fault avoidance", "active fault"],
    "heritage": ["heritage", "notable trees"],
}
OPEN = re.compile(r"creative\s*commons|cc[\s-]*by|cc0|open\s+government\s+licen|attribution\s+4\.0", re.I)
NOT_OPEN = re.compile(r"all rights reserved|not (?:be )?(?:re)?(?:used|distributed)|no(?:t)? licen[cs]e|copyright .* reserved", re.I)
SESSION = requests.Session()


def get(url, **params):
    for attempt in range(4):
        try:
            r = SESSION.get(url, params=dict(params, f="json"), timeout=60)
            if r.status_code == 200: return r.json()
        except requests.RequestException: pass
        time.sleep(2 * (attempt + 1))
    return {}


def text(s):
    return " ".join(re.sub(r"<[^>]+>", " ", s or "").split())


def licence_class(lic, access):
    t = text(lic) + " " + text(access)
    if OPEN.search(t): return "dataset licence"
    if NOT_OPEN.search(t): return "restricted"
    return "none stated" if not text(lic) else "other"


def search(q):
    """Public feature layers in New Zealand matching q."""
    out, start = [], 1
    while start and start <= 400:
        r = get(API + "/search", q=f'({q}) AND (type:"Feature Service" OR type:"Map Service")', bbox=NZ, num=100, start=start)
        out += r.get("results", [])
        start = r.get("nextStart") if r.get("nextStart", -1) > 0 else None
        time.sleep(1)
    return out


def main(out):
    os.makedirs(out, exist_ok=True)
    items, orgs = {}, {}
    for topic, queries in TOPICS.items():
        for q in queries:
            for it in search(q):
                rec = items.setdefault(it["id"], dict(id=it["id"], title=it.get("title"), owner=it.get("owner"), orgid=it.get("orgId"),
                                                     url=it.get("url"), type=it.get("type"), modified=it.get("modified"), topics=set(),
                                                     licence=text(it.get("licenseInfo"))[:400], credits=text(it.get("accessInformation"))[:200]))
                rec["topics"].add(topic)
    for rec in items.values():
        o = rec["orgid"]
        if o and o not in orgs:
            p = get(API + f"/portals/{o}")
            orgs[o] = p.get("name") or o
            time.sleep(0.5)
        rec["org"] = orgs.get(o, o)
        rec["licence_class"] = licence_class(rec["licence"], rec["credits"])
        rec["topics"] = sorted(rec["topics"])
    rows = sorted(items.values(), key=lambda r: (r["org"] or "", r["title"] or ""))
    json.dump(rows, open(os.path.join(out, "council_layers.json"), "w"), indent=1, default=str)
    # per organisation: topics found, and how many items of each have a dataset licence
    by = {}
    for r in rows:
        for t in r["topics"]:
            d = by.setdefault(r["org"], {}).setdefault(t, [0, 0])
            d[0] += 1; d[1] += r["licence_class"] == "dataset licence"
    lines = ["# Council zoning and hazard layers on ArcGIS Online (T-35, T-38)", "",
             f"{len(rows)} public layers inside New Zealand from {len(by)} organisations. Each cell: layers found / of them with an open licence stated on the dataset.", "",
             "| Organisation | " + " | ".join(TOPICS) + " |", "| --- |" + " --- |" * len(TOPICS)]
    for org in sorted(by, key=lambda o: -sum(v[1] for v in by[o].values())):
        lines.append(f"| {org} | " + " | ".join(f"{by[org][t][0]} / {by[org][t][1]}" if t in by[org] else "" for t in TOPICS) + " |")
    lines += ["", "## Licence texts seen (first of each)", ""]
    seen = set()
    for r in rows:
        k = (r["org"], r["licence"][:80])
        if k in seen or not r["licence"]: continue
        seen.add(k); lines.append(f"- {r['org']}: {r['licence'][:300]}")
    open(os.path.join(out, "council_survey.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines[:200]))


if __name__ == "__main__":
    main(sys.argv[1])
