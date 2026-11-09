"""Anywhere in New Zealand, from LINZ data only: the parcel report on demand (T-101, D-21, D-22). See SOURCES.md.

The same pipeline as the councils, with no council layers: parcels, titles and building outlines from LINZ's public
ArcGIS services (the LINZ Data Service by key where it is set, for parcels, titles and easements), and ground and
surface heights from LINZ's national 1 m LiDAR mosaics, read just around the block. parcel_report.py sets the block
around one parcel."""
import os

NAME = "national"
LABEL = "New Zealand (LINZ data only)"
SVC = "https://services.arcgis.com/xdsHIIxuCWByZiCB/arcgis/rest/services"
LINZ_LIC = "LINZ, CC BY 4.0"

ARCGIS = {
    "linz_buildings": (f"{SVC}/LINZ_NZ_Building_Outlines/FeatureServer/0", LINZ_LIC + " (NZ Building Outlines, layer 101290)"),
}
BUILDINGS_CAPTURE = None      # a national layer: its cover is the whole country (`buildings_captured_to` gives its photos' dates)
BUILDINGS_KEY = "linz_buildings"
TITLES_URL = f"{SVC}/LINZ_NZ_Property_Titles/FeatureServer/0"   # titles without the key (title number, status, type only)

PARCELS_URL = f"{SVC}/LINZ_NZ_Primary_Parcels/FeatureServer/0"
PARCELS_COPY = "LINZ ArcGIS service"
PARCELS_VIA, PARCELS_FROM = "LINZ's public ArcGIS service", "LINZ's public ArcGIS service"
PARCELS_KEY = "linz_parcels_service"
OUTLINE = dict(kind="none")   # no district: every parcel whose point is in the block belongs
OUTLINE_LICENCE = "none: the block itself"

LIDAR_BASE = "https://nz-elevation.s3.ap-southeast-2.amazonaws.com/new-zealand/"
LIDAR = [("new-zealand/dem_1m/2193", "dem_national"), ("new-zealand/dsm_1m/2193", "dsm_national")]
LIDAR_KEYS = dict(dem="dem_national", dsm="dsm_national", dem_old=None)
LIDAR_WINDOWED = True         # national sheets are 24 km × 36 km: read the window, never the whole file

POLY_LAYERS = []
POINT_LAYERS = []
POINT_IDS = {}
CLASS_FIELDS = {}
# no national source for these: left out, not published empty (D-12)
ABSENT_COLUMNS = (r"ww_\w+", r"sw_\w+", r"ws_\w+", r"rbl_\w+", r"ground_min_minus_rbl_m", r"dz_2021_2025_\w+",
                  r"lidar_epoch_offset_block_m", r"ovl_\w+", r"flood_\w+", r"wind_stainless", r"wind_very_high",
                  r"tsunami_zones", r"earthworks", r"zones\w*", r"gw_\w+", r"district_share_pct")
RENAME_COLUMNS = {"building_2021_m2": "building_m2"}

DATASET_SOURCES = "public LINZ sources"
SOURCE_KEYS = {"dem_2025": "dem_national", "dsm_2025": "dsm_national", "buildings_2021": "linz_buildings",
               "buildings_capture_area": "district_outline", "kcdc_parcels": PARCELS_KEY}
COLUMN_SOURCES = [(r"building_m2", ["parcels", "dem_national", "linz_buildings"]),
                  (r"buildings_coverage_pct", ["parcels", "linz_buildings"])]

BLOCKS_FILE = None
# the 10 m flow grid around the block: 8 km beyond it for catchments, and written over the LiDAR window and a margin
_X, _Y, _S = (int(os.environ.get(k, d)) for k, d in (("TILE_XMIN", 1769000), ("TILE_YMIN", 5468400), ("TILE_SIZE", 1000)))
FLOW_BBOX = (_X - 8000, _Y - 8000, _X + _S + 8000, _Y + _S + 8000)
FLOW_OUT_BBOX = (_X - 2500, _Y - 2500, _X + _S + 2500, _Y + _S + 2500)

ABOUT = dict(
    licence_note="Values come from LINZ data under CC BY 4.0: attribute LINZ (and each LiDAR survey's producers).",
    boundary=("One parcel's report: the block is the parcel's surroundings. Terrain and surface come from LINZ's "
              "national 1 m LiDAR mosaics, whose surveys range from 2008 to 2026; the report names the survey and "
              "its dates. Building values come from LINZ's national building outlines, drawn from aerial photos, "
              "which miss buildings newer than the photos (unmapped_structure_m2 warns of most, but also flags trees)."),
    empty_values=("An empty value is never a measured 0. Council data (zoning, overlays, flood maps, three waters) "
                  "is not included."))
