"""The public ArcGIS layers fetched for each block (KCDC, GWRC, KCDC building outlines). See SOURCES.md."""
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
