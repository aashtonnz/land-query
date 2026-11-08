"""Kāpiti Coast District: what the pipeline fetches and how the district is defined (T-86). See SOURCES.md."""
NAME = "kapiti"
LABEL = "Kāpiti Coast District"
KC = "https://maps.kapiticoast.govt.nz/server/rest/services/Public"
KC_LIC = "KCDC, CC BY 4.0 (open data portal statement; per-layer status in SOURCES.md)"

ARCGIS = {
    # name: (layer URL, licence note)
    "zones": (f"{KC}/District_Plan_Zones/MapServer/0", KC_LIC),
    "district_boundary": (f"{KC}/Cadastral/MapServer/1", KC_LIC),  # QA: which parcels KCDC clips at the boundary
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

# Where KCDC's 2021 building outlines were captured: the footprint of LINZ's 2017 urban aerial photos, which holds all
# but 2 of the layer's 50,623 outlines (eighth review, T-76). The layer's extent is only this footprint's bounding box.
BUILDINGS_CAPTURE = ("https://nz-imagery.s3.ap-southeast-2.amazonaws.com/wellington/kapiti-coast_2017_0.1m/rgb/2193/capture-area.geojson",
                     "LINZ Kāpiti Coast 0.1 m urban aerial photos (2017) capture area, CC BY 4.0")


# District membership (T-51, T-62, T-65, T-70): candidate parcels from the council's public copy of LINZ parcels;
# the district outline from three boundaries, land where two agree, plus the sea from the line's sea loop.
PARCELS_URL = "https://maps.kapiticoast.govt.nz/server/rest/services/Public/Cadastral/MapServer/0"
PARCELS_COPY = "KCDC mirror"  # geometry_source for a parcel LINZ didn't return
PARCELS_VIA, PARCELS_FROM = "KCDC public mirror", "KCDC's public mirror"  # in its licence notes
PARCELS_KEY = "kcdc_parcels"  # its provenance key and raw file (SOURCES.md register)
OUTLINE = dict(
    # (layer, where, outFields)
    line=(PARCELS_URL.rsplit("/", 1)[0] + "/1", "1=1", "OBJECTID"),           # KCDC's district boundary line
    ward=("https://maps.kapiticoast.govt.nz/server/rest/services/Public/Comm_Board_Ward_Boundaries_2025/MapServer/1",
          "Type='Māori Ward'", "Ward,Type"),                                    # the ward covering the whole district
    stats=("https://mapping.gw.govt.nz/arcgis/rest/services/Region_basemap_P/MapServer/1", "NAME='Kapiti Coast District'", "NAME"),
    sea_x=1735000.0)                                                            # west of Kapiti Island
OUTLINE_LICENCE = KC_LIC + "; Stats NZ district polygon, CC BY 4.0, via GWRC"

# LiDAR surveys (nz-elevation bucket, wellington/): the current DEM and DSM, and an earlier DEM for ground change
LIDAR = [("kapiti-coast_2024-2025/dem_1m/2193", "dem_2025"),
         ("kapiti-coast_2024-2025/dsm_1m/2193", "dsm_2025"),
         ("kapiti-coast_2021/dem_1m/2193", "dem_2021")]

LIDAR_KEYS = dict(dem="dem_2025", dsm="dsm_2025", dem_old="dem_2021")

# what the compiler reads (T-87)
POLY_LAYERS = ["zones", "ovl_flood_hazard", "ovl_ecological_sites", "ovl_noise_corridor", "ovl_coastal_env",
               "flood_river_corridor", "flood_stream_corridor", "flood_overflow_path", "flood_residual_overflow",
               "flood_fill_control", "flood_storage", "flood_ponding", "flood_residual_ponding", "flood_shallow_surface",
               "wind_stainless", "wind_very_high", "tsunami_zones", "earthworks", "ovl_fault_avoidance",
               "gw_liquefaction", "gw_eq_slope_failure"]
POINT_LAYERS = ["ovl_heritage_places", "ovl_notable_trees"]
POINT_IDS = {"ovl_heritage_places": "BUILDING_ID", "ovl_notable_trees": "TREE_ID"}
CLASS_FIELDS = {}          # class fields beyond overlays.class_label's own rules (which are Kāpiti's)
BUILDINGS_KEY = "buildings_2021"
ABSENT_COLUMNS = ()        # regexes of columns this council has no source for
RENAME_COLUMNS = {}

DATASET_SOURCES = "public LINZ, KCDC and GWRC sources"   # in the service's `about`

BLOCKS_FILE = "kapiti_blocks.json"
FLOW_BBOX = (1745000, 5440000, 1835000, 5510000)   # the 10 m district flow mosaic (T-42)
FLOW_OUT_BBOX = (1752000, 5452000, 1808000, 5498000)  # district blocks plus 3 km: every block's LiDAR window

# the query service's `about` (service/landquery.py)
ABOUT = dict(
    licence_note=("Values come from CC BY 4.0 sources; attribute LINZ, Kāpiti Coast District Council and Greater "
                          "Wellington Regional Council as listed per source. In public mode, columns relying on a "
                          "portal-wide licence statement are withheld until confirmed in writing."),
    boundary=("Whole parcels are published. A parcel crossing the district boundary is included if its "
                      "representative point (a point always inside it) or at least 1,000 m2 of it lies in the district, "
                      "so a few parcels reach far outside it (one forest section is 615 km2, about 40 km2 of it in the "
                      "district). Their area covers the whole parcel; terrain covers the part with LiDAR "
                      "(lidar_coverage_pct); building and open-ground values come from KCDC's 2021 building outlines, which "
                      "miss some houses (unmapped_structure_m2 warns of most; it arrives with the next full rebuild where absent), and are empty unless the outlines and the "
                      "fetch window cover the parcel (buildings_coverage_pct, coverage_pct); council layers cover what "
                      "the council maps. "
                      "district_share_pct gives the share inside; it is withheld in public mode until the council licence "
                      "is confirmed (T-35). About 70 railway parcels are not included: the council's parcel list omits them."),
    empty_values=("An empty value is never a measured 0 (a count of recommended building levels is empty "
                          "where there are none). What else it means depends on the column: an empty hazard "
                          "column means the parcel is outside that hazard where the council mapped it, and not mapped "
                          "elsewhere. KCDC's flood layers cover only its flood models, which leave out Kapiti Island, the "
                          "hills and much of the rural north. An empty zones or gw_eq_slope_failure value means not "
                          "mapped; gw_liquefaction maps only soils with significant potential. In public mode some flood "
                          "layers are withheld (see describe_columns), so empty served flood columns do not mean the "
                          "parcel is outside every flood layer."))
