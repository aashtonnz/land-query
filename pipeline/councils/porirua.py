"""Porirua City: what the pipeline fetches and how the city is defined (T-87). See SOURCES.md.

District Plan layers are the Porirua District Plan 2025, operative from 1 November 2025, from PCC's ArcGIS Online
organisation. Three waters are left out: Wellington Water's licence bars commercial use (D-16)."""
NAME = "porirua"
LABEL = "Porirua City"
A = "https://services1.arcgis.com/kIwRm3UCyRHYbM8a/arcgis/rest/services"
P = "https://maps.poriruacity.govt.nz/server/rest/services"
PCC_LIC = "PCC, CC BY 4.0 (open data portal statement; per-layer status in SOURCES.md)"
GW_LIC = "GWRC, CC BY 4.0 unless stated (regional statement; see SOURCES.md)"
fs = lambda name: (f"{A}/{name}/FeatureServer/0", PCC_LIC)

ARCGIS = {
    "zones": fs("Zone_PDP2025"),
    "pdp_flood_overland_flow": fs("Flood_Hazard_Overland_Flow_PDP2025"),
    "pdp_flood_stream_corridor": fs("Flood_Hazard_Stream_Corridor_PDP2025"),
    "pdp_flood_inundation": fs("Flood_Hazard_Inundation_PDP2025"),
    "pdp_coastal_erosion_current": fs("Coastal_Erosion_Hazard_Current_Erosion_Risk_PDP2025"),
    "pdp_coastal_erosion_1m_slr": fs("Coastal_Erosion_Hazard_Future_Erosion_with_1m_SLR_PDP2025"),
    "pdp_coastal_inundation_current": fs("Coastal_Flood_Hazard_Current_Inundation_Risk_PDP2025"),
    "pdp_coastal_inundation_1m_slr": fs("Coastal_Flood_Hazard_1in100yr_Storm_Surge_with_1m_SLR_PDP2025"),
    "pdp_tsunami_100yr": fs("Tsunami_Hazard_1in100yr_Inundation_PDP2025"),
    "pdp_tsunami_500yr": fs("Tsunami_Hazard_1in500yr_Inundation_PDP2025"),
    "pdp_tsunami_1000yr": fs("Tsunami_Hazard_1in1000yr_Inundation_PDP2025"),
    "pdp_fault_rupture": fs("Fault_Rupture_Zone_PDP2025"),
    "pdp_heritage_items": fs("Heritage_Item_PDP2025"),
    "pdp_heritage_sites": fs("Historic_Heritage_Site_PDP2025"),
    "pdp_notable_trees": fs("Notable_Tree_PDP2025"),
    "pdp_significant_natural_areas": fs("Significant_Natural_Areas_PDP2025"),
    "pdp_noise_rail": fs("Rail_Noise_Corridor_PDP2025"),
    "pdp_noise_state_highway": fs("State_Highway_Noise_Control_Boundary_PDP2025"),
    "pdp_coastal_environment": fs("Landward_Extent_Coastal_Environment_PDP2025"),
    "gw_liquefaction": ("https://mapping.gw.govt.nz/arcgis/rest/services/GW/Emergencies_P/MapServer/10", GW_LIC),
    "gw_eq_slope_failure": ("https://mapping.gw.govt.nz/arcgis/rest/services/GW/Emergencies_P/MapServer/11", GW_LIC),
    "pcc_buildings": (f"{P}/Property/PropertyAdminExternal/MapServer/2", PCC_LIC),
}
# PCC's footprints span the city (their extent matches its boundary), so their coverage is the city itself; the
# LiDAR warning column (unmapped_structure_m2) checks for buildings they miss
BUILDINGS_CAPTURE = None
BUILDINGS_KEY = "pcc_buildings"

PARCELS_URL = f"{P}/Property/Parcel/MapServer/2"   # PCC's copy of LINZ NZ Primary Parcels (same fields as KCDC's)
PARCELS_COPY = "PCC mirror"
PARCELS_VIA, PARCELS_FROM = "PCC public mirror", "PCC's public mirror"
PARCELS_KEY = "pcc_parcels"
# three boundary polygons; land counts where two agree (overlays.district_outline_polygons)
OUTLINE = dict(
    kind="polygons",
    line=(f"{P}/Property/PropertyAdminExternal/MapServer/4", "1=1", "OBJECTID"),        # PCC's city boundary
    ward=("https://services1.arcgis.com/kIwRm3UCyRHYbM8a/arcgis/rest/services/Ward/FeatureServer/3", "1=1", "WARD_NAME"),
    stats=("https://mapping.gw.govt.nz/arcgis/rest/services/Region_basemap_P/MapServer/1", "NAME='Porirua City'", "NAME"),
    sea_x=None)
OUTLINE_LICENCE = PCC_LIC + "; Stats NZ district polygon, CC BY 4.0, via GWRC"

LIDAR = [("porirua_2023/dem_1m/2193", "dem_2023"), ("porirua_2023/dsm_1m/2193", "dsm_2023")]
LIDAR_KEYS = dict(dem="dem_2023", dsm="dsm_2023", dem_old=None)   # one survey: no ground-change columns

POLY_LAYERS = ["zones", "pdp_flood_overland_flow", "pdp_flood_stream_corridor", "pdp_flood_inundation",
               "pdp_coastal_erosion_current", "pdp_coastal_erosion_1m_slr", "pdp_coastal_inundation_current",
               "pdp_coastal_inundation_1m_slr", "pdp_tsunami_100yr", "pdp_tsunami_500yr", "pdp_tsunami_1000yr",
               "pdp_fault_rupture", "pdp_heritage_sites", "pdp_significant_natural_areas", "pdp_noise_rail",
               "pdp_noise_state_highway", "pdp_coastal_environment", "gw_liquefaction", "gw_eq_slope_failure"]
POINT_LAYERS = ["pdp_heritage_items", "pdp_notable_trees"]
POINT_IDS = {"pdp_heritage_items": "ID", "pdp_notable_trees": "Tree_ID"}
CLASS_FIELDS = {   # (fields to try, name when none is set)
    "zones": (("ZONE",), "Zone not recorded"),
    "pdp_fault_rupture": (("Fault_Name",), "Fault rupture zone"),
    "pdp_heritage_sites": (("Name",), "Historic heritage site"),
    "pdp_significant_natural_areas": (("SiteName",), "Significant natural area"),
    "pdp_flood_overland_flow": ((), "Overland flow"), "pdp_flood_stream_corridor": ((), "Stream corridor"),
    "pdp_flood_inundation": ((), "Inundation"),
    "pdp_coastal_erosion_current": ((), "Current coastal erosion"),
    "pdp_coastal_erosion_1m_slr": ((), "Coastal erosion with 1 m sea-level rise"),
    "pdp_coastal_inundation_current": ((), "Current coastal inundation"),
    "pdp_coastal_inundation_1m_slr": ((), "1-in-100-year storm surge with 1 m sea-level rise"),
    "pdp_tsunami_100yr": ((), "1-in-100-year tsunami"), "pdp_tsunami_500yr": ((), "1-in-500-year tsunami"),
    "pdp_tsunami_1000yr": ((), "1-in-1000-year tsunami"),
    "pdp_noise_rail": (("Type",), "Rail noise corridor"), "pdp_noise_state_highway": ((), "State highway noise control"),
    "pdp_coastal_environment": ((), "Coastal environment"),
}
# no source for these in Porirua: left out, not published empty (D-12)
ABSENT_COLUMNS = (r"ww_\w+", r"sw_\w+", r"ws_\w+", r"rbl_\w+", r"ground_min_minus_rbl_m", r"dz_2021_2025_\w+",
                  r"lidar_epoch_offset_block_m",
                  # Kāpiti's own overlays: Porirua's are the pdp_* columns
                  r"ovl_\w+", r"flood_\w+", r"wind_stainless", r"wind_very_high", r"tsunami_zones", r"earthworks")
RENAME_COLUMNS = {"building_2021_m2": "building_m2"}   # PCC's footprints are not the 2021 KCDC capture

DATASET_SOURCES = "public LINZ, Porirua City Council and GWRC sources"
# Kāpiti's source keys (service/catalogue.py COLUMN_SOURCES) as Porirua names them
SOURCE_KEYS = {"dem_2025": "dem_2023", "dsm_2025": "dsm_2023", "buildings_2021": "pcc_buildings",
               "buildings_capture_area": "district_outline", "kcdc_parcels": "pcc_parcels"}
COLUMN_SOURCES = [(r"building_m2", ["parcels", "dem_2023", "pcc_buildings"]),
                  (r"pdp_\w+", None)]   # a District Plan layer: its own source key

BLOCKS_FILE = "porirua_blocks.json"
FLOW_BBOX = (1740000, 5432000, 1780000, 5468000)       # the city plus room for catchments draining into it
FLOW_OUT_BBOX = (1743000, 5436000, 1772000, 5464000)  # every block's LiDAR window (T-87 test)
