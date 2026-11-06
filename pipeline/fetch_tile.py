"""Fetch the block's fetch window from public KCDC and GWRC layers, logging provenance.

Every fetched source is written to data/raw/ and recorded in data/provenance.json with
URL, fetch time, sha256, feature count and licence note. Nothing is invented: a source
that fails is recorded as failed.
"""
import hashlib, json, os, sys, time, datetime as dt
import requests
import tile_env as te

OUT = sys.argv[1] if len(sys.argv) > 1 else "data"
_W = te.fetch_bbox(OUT)  # block grown to cover its parcels (fetch_parcels_kcdc.py)
TILE = dict(xmin=_W[0], ymin=_W[1], xmax=_W[2], ymax=_W[3])  # NZTM2000 (EPSG:2193)
RAW = os.path.join(OUT, "raw"); os.makedirs(RAW, exist_ok=True)
KC = "https://maps.kapiticoast.govt.nz/server/rest/services/Public"
KC_LIC = "KCDC, CC BY 4.0 (open data portal statement; per-layer status in SOURCES.md)"

ARCGIS = {
    # name: (layer URL, licence note)
    "zones": (f"{KC}/District_Plan_Zones/MapServer/0", KC_LIC),
    "ovl_fault_avoidance": (f"{KC}/District_Plan_Overlays/MapServer/10", KC_LIC),
    "ovl_flood_hazard": (f"{KC}/District_Plan_Overlays/MapServer/11", KC_LIC),
    "ovl_heritage_places": (f"{KC}/District_Plan_Overlays/MapServer/14", KC_LIC),
    "ovl_notable_trees": (f"{KC}/District_Plan_Overlays/MapServer/16", KC_LIC),
    "ovl_ecological_sites": (f"{KC}/District_Plan_Overlays/MapServer/19", KC_LIC),
    "ovl_noise_corridor": (f"{KC}/District_Plan_Overlays/MapServer/28", KC_LIC),
    "ovl_coastal_env": (f"{KC}/District_Plan_Overlays/MapServer/30", KC_LIC),
    "flood_river_corridor": (f"{KC}/Latest_Flood_Hazards/MapServer/0", KC_LIC),
    "flood_stream_corridor": (f"{KC}/Latest_Flood_Hazards/MapServer/1", KC_LIC),
    "flood_overflow_path": (f"{KC}/Latest_Flood_Hazards/MapServer/2", KC_LIC),
    "flood_residual_overflow": (f"{KC}/Latest_Flood_Hazards/MapServer/3", KC_LIC),
    "flood_fill_control": (f"{KC}/Latest_Flood_Hazards/MapServer/4", KC_LIC),
    "flood_storage": (f"{KC}/Latest_Flood_Hazards/MapServer/5", KC_LIC),
    "flood_ponding": (f"{KC}/Latest_Flood_Hazards/MapServer/6", KC_LIC),
    "flood_residual_ponding": (f"{KC}/Latest_Flood_Hazards/MapServer/7", KC_LIC),
    "flood_shallow_surface": (f"{KC}/Latest_Flood_Hazards/MapServer/8", KC_LIC),
    "flood_rbl_nzvd2016": (f"{KC}/Latest_Flood_Hazards/MapServer/10", KC_LIC),
    "ww_node": (f"{KC}/Services_Open_Data/MapServer/9", KC_LIC),
    "ww_pipe": (f"{KC}/Services_Open_Data/MapServer/10", KC_LIC),
    "ww_lateral": (f"{KC}/Services_Open_Data/MapServer/11", KC_LIC),
    "sw_point": (f"{KC}/Services_Open_Data/MapServer/4", KC_LIC),
    "sw_pipe": (f"{KC}/Services_Open_Data/MapServer/5", KC_LIC),
    "ws_pipe": (f"{KC}/Services_Open_Data/MapServer/2", KC_LIC),
    "wind_stainless": (f"{KC}/Wind_and_Corrosion/MapServer/1", KC_LIC),
    "wind_very_high": (f"{KC}/Wind_and_Corrosion/MapServer/2", KC_LIC),
    "tsunami_zones": (f"{KC}/Tsunami/MapServer/3", KC_LIC),
    "earthworks": (f"{KC}/Earthworks/MapServer/1", KC_LIC),
    "gw_liquefaction": ("https://mapping.gw.govt.nz/arcgis/rest/services/GW/Emergencies_P/MapServer/10",
                        "GWRC, CC BY 4.0 unless stated (regional statement; see SOURCES.md)"),
    "gw_eq_slope_failure": ("https://mapping.gw.govt.nz/arcgis/rest/services/GW/Emergencies_P/MapServer/11",
                            "GWRC, CC BY 4.0 unless stated (regional statement; see SOURCES.md)"),
    "buildings_2021": ("https://services2.arcgis.com/quz2eeKTvR4p12uf/arcgis/rest/services/Building_Outlines_2021/FeatureServer/0",
                       "KCDC Building Outlines 2021, CC BY 4.0 (portal statement; see SOURCES.md)"),
}

def sha(b): return hashlib.sha256(b).hexdigest()

def arcgis_query(url):
    """Page through an ArcGIS layer for features intersecting the fetch window, as GeoJSON in EPSG:2193."""
    feats, offset = [], 0
    try: page = int(requests.get(url, params={"f": "json"}, timeout=60).json().get("maxRecordCount") or 1000)
    except Exception: page = 1000
    page = max(1000, min(page, 5000))
    env = f"{TILE['xmin']},{TILE['ymin']},{TILE['xmax']},{TILE['ymax']}"
    while True:
        p = dict(where="1=1", geometry=env, geometryType="esriGeometryEnvelope", inSR=2193,
                 spatialRel="esriSpatialRelIntersects", outFields="*", outSR=2193,
                 returnGeometry="true", f="geojson", resultOffset=offset, resultRecordCount=page)
        for attempt in range(4):
            try:
                r = requests.get(url + "/query", params=p, timeout=120)
                r.raise_for_status()
                break
            except requests.exceptions.RequestException:
                if attempt == 3: raise
                time.sleep(5 * (attempt + 1))
        j = r.json()
        if "error" in j: raise RuntimeError(j["error"])
        fs = j.get("features", [])
        feats += fs
        if len(fs) < page and not j.get("exceededTransferLimit"): break
        offset += len(fs)
    return {"type": "FeatureCollection", "features": feats}

def main():
    pp = os.path.join(OUT, "provenance.json")
    prov = json.load(open(pp)) if os.path.exists(pp) else {"sources": {}}
    prov.update(tile_nztm=TILE, fetched_at=dt.datetime.now(dt.timezone.utc).isoformat())
    only = set(os.environ.get("ONLY", "").split(",")) - {""}
    for name, (url, lic) in ARCGIS.items():
        if only and name not in only: continue
        t0 = time.time()
        try:
            fc = arcgis_query(url)
            b = json.dumps(fc).encode()
            open(os.path.join(RAW, name + ".geojson"), "wb").write(b)
            meta = requests.get(url, params={"f": "json"}, timeout=60).json()
            prov["sources"][name] = dict(url=url, ok=True, features=len(fc["features"]), bytes=len(b), sha256=sha(b),
                                         seconds=round(time.time() - t0, 2), licence=lic,
                                         layer_name=meta.get("name"), copyright=te.scrub_copyright(meta.get("copyrightText")))
            print(f"{name:26s} {len(fc['features']):6d} features  {time.time()-t0:5.1f}s")
        except Exception as e:
            prov["sources"][name] = dict(url=url, ok=False, error=str(e)[:300], licence=lic)
            print(f"{name:26s} FAILED {e}")
    json.dump(prov, open(os.path.join(OUT, "provenance.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
