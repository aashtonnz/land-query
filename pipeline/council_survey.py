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
OPEN = re.compile(r"creative\s*commons|cc[\s-]*by|cc0|open\s+government\s+licen|attribution\s+[34]\.0", re.I)
NC_ND = re.compile(r"non[\s-]*commercial|\bnc\b|by-nc|noderiv|no[\s-]*derivatives|by-nd|\bnd\b|educational (?:use|purposes) only|not .{0,30}commercial", re.I)
SA = re.compile(r"share[\s-]*alike|by-sa", re.I)
NOT_OPEN = re.compile(r"all rights reserved|not (?:be )?(?:re)?(?:used|distributed)|no(?:t)? licen[cs]e|copyright .* reserved|must not be distributed|only\.?$", re.I)
NZ_BOX = (160.0, -53.0, 185.0, -28.0)   # an item's own extent must lie inside this, and be under 15 degrees across
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


CLAUSE = re.compile(r"not permitted to (?:copy|republish)|without the (?:prior )?written consent|must not be (?:copied|republished)|may not be used for the purposes? of any legal", re.I)


def licence_class(lic, access):
    t = text(lic) + " " + text(access)
    if OPEN.search(t):
        if NC_ND.search(t): return "non-commercial or no-derivatives"
        # an open licence beside a clause that takes it back (Auckland Council: CC BY 4.0, yet "not permitted to copy or
        # republish any substantial amount ... without the prior written consent"): for the council to confirm (T-35)
        if CLAUSE.search(t): return "open licence with a restricting clause"
        if SA.search(t): return "share-alike"
        return "dataset licence"
    if NOT_OPEN.search(t): return "restricted"
    return "none stated" if not text(lic) else "other"


def in_nz(extent):
    """True if an item's extent [[xmin, ymin], [xmax, ymax]] (lon/lat) lies in New Zealand and is not the world."""
    try: (x0, y0), (x1, y1) = extent
    except (TypeError, ValueError): return False
    return NZ_BOX[0] <= x0 <= x1 <= NZ_BOX[2] and NZ_BOX[1] <= y0 <= y1 <= NZ_BOX[3] and x1 - x0 < 15


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
                if not in_nz(it.get("extent")): continue
                rec = items.setdefault(it["id"], dict(id=it["id"], title=it.get("title"), owner=it.get("owner"), orgid=it.get("orgId"),
                                                     url=it.get("url"), type=it.get("type"), modified=it.get("modified"), topics=set(),
                                                     licence=text(it.get("licenseInfo"))[:1200], credits=text(it.get("accessInformation"))[:200]))
                rec["topics"].add(topic)
    # ArcGIS Online's search gives no organisation, so each layer is grouped by the server it lives on (a council's own
    # server, or an ArcGIS Online account's key in the address), and the group named by the credit its layers state most
    def server(url):
        m = re.match(r"https?://([^/]+)(/[^/]+)?", url or "")
        return (m.group(1) + (m.group(2) or "")) if m else "(no service address)"
    groups = {}
    for rec in items.values():
        rec["server"] = server(rec["url"])
        groups.setdefault(rec["server"], []).append(rec)
    for key, recs in groups.items():
        cr = {}
        for r in recs:
            if r["credits"]: cr[r["credits"][:70]] = cr.get(r["credits"][:70], 0) + 1
        name = max(cr.items(), key=lambda kv: kv[1])[0] if cr else ""
        for r in recs:
            r["org"] = (name + " " if name else "") + "(" + key + ")"
            r["licence_class"] = licence_class(r["licence"], r["credits"])
    for r in items.values(): r["topics"] = sorted(r["topics"])   # a list in the JSON, not a set's text
    rows = sorted(items.values(), key=lambda r: (r["org"] or "", r["title"] or ""))
    json.dump(rows, open(os.path.join(out, "council_layers.json"), "w"), indent=1, default=str)
    # per organisation: topics found, and how many items of each have a dataset licence
    by = {}
    for r in rows:
        for t in r["topics"]:
            d = by.setdefault(r["org"], {}).setdefault(t, [0, 0, 0])
            d[0] += 1; d[1] += r["licence_class"] == "dataset licence"; d[2] += r["licence_class"] == "non-commercial or no-derivatives"
    lines = ["# Council zoning and hazard layers on ArcGIS Online (T-35, T-38)", "",
             f"{len(rows)} public layers inside New Zealand from {len(by)} organisations. Each cell: layers found / with an open licence (CC BY or similar, commercial use allowed) written on the dataset / with a non-commercial or no-derivatives licence.", "",
             "| Organisation | " + " | ".join(TOPICS) + " |", "| --- |" + " --- |" * len(TOPICS)]
    for org in sorted(by, key=lambda o: -sum(v[1] for v in by[o].values())):
        lines.append(f"| {org} | " + " | ".join(f"{by[org][t][0]} / {by[org][t][1]} / {by[org][t][2]}" if t in by[org] else "" for t in TOPICS) + " |")
    lines += ["", "## Open zoning and hazard layers (dataset licence)", ""]
    for r in rows:
        if r["licence_class"] == "dataset licence" and set(r["topics"]) & {"zoning", "flood", "coastal", "land"}:
            lines.append(f"- {r['org']}: {r['title']} ({', '.join(r['topics'])}) {r['url'] or ''}")
    open(os.path.join(out, "council_survey.md"), "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1])
