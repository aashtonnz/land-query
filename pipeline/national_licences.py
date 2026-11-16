"""The licence LINZ states for each ArcGIS service layer the national index reads (T-104): national_licences.py.

Prints, per layer, the ArcGIS Online item's title, licence text, credits and any LINZ Data Service layer it names, as
markdown, so the weekly source check records it. The item catalogue (www.arcgis.com) is reachable from GitHub's
runners, not from every session.
"""
import html, re, sys
import requests
import national_index as N

ITEM = "https://www.arcgis.com/sharing/rest/content/items/"


def text(s):
    return " ".join(re.sub(r"<[^>]+>", " ", html.unescape(s or "")).split())


def main():
    print("## Licences of the national index's service layers (T-104)\n")
    for k in ("parcels", "addresses", "buildings", "titles", "coast", "land", "lakes", "rivers", "localities"):
        svc = N.LAYERS[k][0]
        try:
            iid = requests.get(N.SVC + svc + "/FeatureServer", params=dict(f="json"), timeout=60).json().get("serviceItemId")
            it = requests.get(ITEM + str(iid), params=dict(f="json"), timeout=60).json()
            lds = sorted(set(re.findall(r"data\.linz\.govt\.nz/(?:layer|table)/(\d+)", " ".join(str(it.get(f) or "") for f in ("description", "snippet", "licenseInfo")))))
            print(f"- **{k}** ({svc}, item {iid}): {it.get('title')!r}. Licence: {text(it.get('licenseInfo'))[:600] or 'none stated'}. "
                  f"Credits: {text(it.get('accessInformation'))[:200] or 'none'}. Data Service layers named: {', '.join(lds) or 'none'}")
        except Exception as e:
            print(f"- **{k}** ({svc}): could not read: {e}")


if __name__ == "__main__":
    sys.exit(main())
